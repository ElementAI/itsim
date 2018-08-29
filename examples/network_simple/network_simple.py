from contextlib import contextmanager
from itertools import chain
import logging
from typing import Generator

from greensim import Simulator, Signal
from greensim.logging import Filter
from greensim.random import VarRandom, constant, normal, expo, uniform, distribution

from itsim import MS, US, H, GbPS
from itsim.network import Network, Internet
from itsim.node import Endpoint
from itsim.random import num_bytes


NUM_ENDPOINTS = 50


def get_logger(name_logger):
    logger = logging.getLogger(name_logger)
    logger.addFilter(Filter())
    logger.setFormatter(logging.Formatter("%(sim_time)f [%(sim_process)s] %(message)s"))
    return logger


def _throw_process(proc, exc):  # FIXME -- Move that somehow in greensim
    proc.rsim()._schedule(proc.throw, exc)


# FIXME -- Push this in endpoints, or in nodes?
class Workstation(Endpoint):

    def __init__(self, name: str, network: Network, ar: AddressRepr = None, *forward_to: CidrRepr) -> None:
        super().__init__(name, network, ar, *forward_to)
        self._wake = Signal().turn_off()
        self._time_awoken = -1.0

    def wake_up(self) -> None:
        self._wake.turn_on()
        self._time_awoken = now()

    def sleep(self) -> None:
        self._wake.turn_off()
        self._time_awoken = -1.0

    def is_awake(self) -> bool:
        return self._wake.is_on

    def wait_until_awake(self) -> None:
        self._wake.wait()

    class FellAsleep(Exception):
        pass

    @contextmanager
    def awake(self) -> Generator["Workstation", None, None]:
        self.wait_until_awake()
        time_at_start = self._time_awoken
        yield self
        if now() != self._time_awoken:
            raise Workstation.FellAsleep()

    class _Complete(Exception):
        pass

    class Timeout(Exception):
        pass

    @contextmanager
    def timeout(self, delay) -> Generator["Workstation", None, None]:
        proc_timeout = add(self._wait_for_timeout, delay, Process.current())
        try:
            yield self
            _throw_process(proc_timeout, Workstation._Complete())
        except Workstation._Complete:
            raise Workstation.Timeout()

    def _wait_for_timeout(self, delay, process_main):
        try:
            advance(delay)
            _throw_process(process_main, Workstation._Complete())
        except Workstation._Complete:
            pass


delay_workstation_awake = expo(2.0 * H)
delay_workstation_sleeping = expo(10.0 * MIN)
delay_setup_to_ready = expo(5.0 * US)


def workstation_blinking(ws: Workstation) -> None:
    logger = get_logger("blinking")
    local.name = f"{node.name} blinking"

    while True:
        ws.is_awake.turn_off()
        advance(next(delay_workstation_sleeping))

        logger.debug(f"Awakening; redo networking setup")
        get_address_from_dhcp(ws)
        claim_name_through_mdns(ws)
        advance(next(delay_setup_to_ready))
        ws.is_awake.turn_on()
        logger.info(f"Awake (got address on the network)")
        advance(next(delay_workstation_awake))

        logger.debug(f"Sleep")


size_packet_dhcp = num_bytes(normal(100.0 * B, 30.0 * B), header=240 * B)


def get_address_from_dhcp(ws: Workstation) -> None:
    logger = get_logger("dhcp_client")
    with ws.open_socket(68) as socket:
        # DHCP server discovery.
        socket.broadcast(67, next(size_packet_dhcp), Payload({"msg": "DHCPDISCOVERY"}))  # FIXME
        # Lease offer.
        packet_offer = socket.recv()
        logger.info(f"{packet_offer.payload.entries['msg']} from {packet_offer.src.host}")  # FIXME
        # Address request.
        socket.send(packet_offer.src, next(size_packet_dhcp), Payload({"msg": "DHCPREQUEST"}))  # FIXME
        # Address acknowledgement.
        packet_ack = socket.recv()
        logger.info(f"{packet_ack.payload.entries['msg']} from {packet_ack.src.host}")  # FIXME


def dhcp_payload(msg_name: str) -> Payload:
    return Payload({"msg": msg_name})


def dhcp_serve(ws: Workstation) -> None:
    local.name = f"DHCP server / {ws.name}"
    responses = {"DHCPDISCOVER": "DHCPOFFER", "DHCPREQUEST": "DHCPACK"}
    with ws.open_socket(67) as socket:
        while True:
            # On reception of server discovery and address request packets, send the corresponding response.
            packet_client = socket.recv()
            type_msg = packet_client.payload.entries["msg"]
            if type_msg not in responses:
                logger.warning(f"Received unknown message {repr(type_msg)} from {packet_client.src.host} -- DROP")
            else:
                logger.info(f"Received {type_msg} from {packet_client.src.host}")
                socket.send(packet_client.src, next(size_packet_dhcp), dhcp_payload(responses[type_msg]))


# Used by both mDNS and LLMNR responders.
size_packet_dns = num_bytes(expo(192.0 * B), header=68 * B, upper=576 * B)


def mdns_daemon(ws: Workstation) -> None:
    # This models only mDNS local host name resolution; service discovery is TBD.
    local.name = "mDNS responder / {ws.name}"
    logger = get_logger("mdns_responder")
    while True:
        queries = []
        try:
            with ws.open_socket(5353) as socket:
                while True:
                    with ws.awake():
                        packet = socket.recv()
                    pl_ent = packet.payload.entries

                    if pl_ent["msg"] == "query":
                        queries.append(packet)
                        socket.broadcast(
                            5353,
                            packet.num_bytes,
                            Payload({"msg": "resolve", "hostname": pl_ent["hostname"]})
                        )  # FIXME -- add port info

                    elif pl_ent["msg"] == "iam":
                        i_del = None
                        for i, packet_query in enumerate(queries):
                            if packet_query.payload.entries["hostname"] == pl_ent["hostname"]:
                                i_del = i
                                socket.send(packet_query.src, packet.num_bytes, packet.payload)
                                break
                        if i_del is not None:
                            del queries[i_del]

                    elif pl_ent["msg"] == "resolve" and pl_ent["hostname"] == ws.name:
                        logger.info(f"Resolve hostname {ws.name} as {ws.address_default}")
                        socket.broadcast(
                            5353,
                            next(size_packet_dns),
                            Payload({"msg": "iam", "hostname": ws.name, "address": self.address_default})
                        )  # FIXME

        except Workstation.FellAsleep:
            # This mechanism encodes the inevitable drop of packets and loss of socket inherent to wake-cycling the
            # workstation.
            logger.debug("Reset by workstation falling asleep")


def llmnr_daemon(ws: Workstation) -> None:
    local.name = "LLMNR responder / {ws.name}"
    logger = get_logger("llmnr_responder")
    while True:
        try:
            with ws.open_socket(5355) as socket:
                while True:
                    with ws.awake():
                        packet = socket.recv()
                    payload_entries = packet.payload.entries
                    if payload_entries["msg"] == "resolve" and payload_entries["hostname"] == ws.name:
                        logger.info(f"Resolve hostname {ws.name} as {ws.address_default}")
                        socket.send(
                            packet.src,
                            next(size_packet_dns),
                            Payload({"msg": "iam", "hostname": ws.name, "address": self.address_default})
                        )
        except Workstation.FellAsleep:
            logger.debug("Reset by workstation falling asleep")


delay_identity_queries = expo(2.0 * MIN)
size_packet_delta = normal(0.0 * B, 10.0 * B)


@contextmanager
def _query(protocol: str, logger: logging.Logger, ws: Workstation, size_packet_base: int, payload: Payload):
    try:
        local.name = f"{protocol} query from {ws.name}"
        with ws.open_socket() as socket:
            yield socket, size_packet_base + next(size_packet_delta)
            try:
                with ws.awake(), ws.timeout(5.0):  # FIXME - fugly
                    response = socket.recv()
                    rpl = response.payload.entries
                    logger.info(f"{rpl['hostname']} resolved to {rpl['address']}")
            except Workstation.Timeout:
                logger.debug(f"Resolution of {payload.entries['hostname']} timed out")
    except Workstation.FellAsleep:
        logger.debug(f"Resolution of {payload.entries['hostname'] killed by workstation falling asleep")


def _query_mdns(logger: logging.Logger, ws: Workstation, size_packet_base: int, payload: Payload):
    with _query("mDNS", logger, ws, size_packet_base, payload) as socket, size_packet:
        socket.send(Location(ws.address_default, 5353), size_packet, payload)


def _query_llmnr(logger: logging.Logger, ws: Workstation, size_packet_base: int, payload: Payload):
    with _query("LLMNR", logger, ws, size_packet_base, payload) as socket, size_packet:
        socket.broadcast(5355, size_packet, payload)


def client_activity(ws: Workstation, name_next_query: VarRandom[str]) -> None:
    local.name = f"Client activity / {ws.name}"
    logger = get_logger("client_activity")
    while True:
        ws.wait_until_awake()
        try:
            with ws.awake():
                advance(next(delay_identity_queries))

            target_query = next(name_next_query)
            logger.info(f"Query IP address of {target_query}")

            payload = Payload({"msg": "resolve", "hostname": query_target})
            size_packet_base = next(size_packet_dns)
            for q in [_query_mdns, _query_llmnr]:
                add(q, logger, ws, size_packet_base, payload)
        except Workstation.FellAsleep:
            logger.debug("Reset by machine falling asleep")


if __name__ == '__main__':
    logger = logging.getLogger()
    logger.addFilter(Filter())
    logger.setLevel(logging.INFO)

    with Simulator() as sim:
        net_local = Network(
            sim,
            cidr="192.168.4.0/24",
            bandwidth=constant(1 * GbPS),
            latency=normal(5 * MS, 1 * MS)
        )

        num_workstations = NUM_ENDPOINTS - 1  # DHCP server is not a workstation.
        num_mdns = int(0.9 * num_workstations)
        num_llmnr = num_workstations - num_mdns
        dhcp_server = Endpoint("DHCPServer", net_local, "192.168.4.2").install(dhcp_serve)
        workstations = [
            Workstation(f"Workstation-{n+1}", net_local).install(
                workstation_blinking,
                self_identification_service
            )
            for n, self_indentification_service in enumerate(
                chain((mdns_respond for _ in range(num_mdns)), (llmnr_respond for _ in range(num_llmnr)))
            )
        ]

        name_next_query = distribution([ws.name for ws in workstations])
        for ws in workstations:
            ws.install(client_activity, name_next_query)

        sim.run(12 * H)
