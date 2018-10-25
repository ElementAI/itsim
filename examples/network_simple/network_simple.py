import argparse
from contextlib import contextmanager
from ipaddress import ip_network
import logging
import sys
from typing import Generator, Optional

from greensim import Simulator, Signal, advance, local, now, Process, add
from greensim.logging import Filter
from greensim.random import VarRandom, constant, normal, expo, distribution

from itsim.network.location import Location
from itsim.network.packet import Payload, PayloadDictionaryType
from itsim.random import num_bytes
from itsim.types import AddressRepr, CidrRepr
from itsim.units import MS, US, MIN, H, B, GbPS

from network_simple_overrides import Endpoint, Network


NUM_ADDRESSES_RESERVED = 2  # Address 0 and broadcast address.
MIN_NUM_WORKSTATIONS = 2
MIN_NUM_ENDPOINTS = MIN_NUM_WORKSTATIONS + 1


def get_logger(name_logger=__name__):
    logger = logging.getLogger(name_logger)
    if len(logger.handlers) == 0:
        logger.setLevel(logging.getLogger().level)
        logger.addFilter(Filter())
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(logging.Formatter("<%(levelname)s> %(sim_time)f [%(sim_process)s] %(message)s"))
        logger.addHandler(handler)
    return logger


def _throw_process(proc, exc):  # FIXME -- Move that somehow in greensim
    proc.rsim()._schedule(0.0, proc.throw, exc)


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

    def wait_until_awake(self, logger: Optional[logging.Logger] = None) -> None:
        time_before = self._time_awoken
        self._wake.wait()
        if self._time_awoken != time_before:
            if logger:
                logger.debug("Resuming after machine awoke")

    class FellAsleep(Exception):
        pass

    @contextmanager
    def awake(self) -> Generator["Workstation", None, None]:
        self.wait_until_awake()
        time_at_start = self._time_awoken
        yield self
        if self._time_awoken != time_at_start:
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
    local.name = f"{ws.name} / Blinking"

    while True:
        ws.sleep()
        advance(next(delay_workstation_sleeping))

        logger.debug(f"Awakening; redo networking setup")
        get_address_from_dhcp(ws)
        advance(next(delay_setup_to_ready))
        ws.wake_up()
        logger.info(f"Awake (got address on the network)")
        advance(next(delay_workstation_awake))

        logger.debug(f"Sleep")


def dhcp_payload(msg_name: str) -> Payload:
    return Payload({PayloadDictionaryType.CONTENT: msg_name})


size_packet_dhcp = num_bytes(normal(100.0 * B, 30.0 * B), header=240 * B)


def get_address_from_dhcp(ws: Workstation) -> None:
    logger = get_logger("dhcp_client")
    with ws.open_socket(68) as socket:
        # DHCP server discovery.
        socket.broadcast(67, next(size_packet_dhcp), Payload({PayloadDictionaryType.CONTENT: "DHCPDISCOVER"}))  # FIXME
        # Lease offer.
        packet_offer = socket.recv()
        logger.info("%s from %s" %
                    (packet_offer.payload.entries[PayloadDictionaryType.CONTENT],
                     packet_offer.source.hostname))  # FIXME
        # Address request.
        socket.send(packet_offer.source,
                    next(size_packet_dhcp),
                    Payload({PayloadDictionaryType.CONTENT: "DHCPREQUEST"}))  # FIXME
        # Address acknowledgement.
        packet_ack = socket.recv()
        logger.info("%s from %s" %
                    (packet_ack.payload.entries[PayloadDictionaryType.CONTENT],
                     packet_ack.source.hostname))  # FIXME


def dhcp_serve(ws: Workstation) -> None:
    local.name = f"{ws.name} / DHCP server"
    responses = {"DHCPDISCOVER": "DHCPOFFER", "DHCPREQUEST": "DHCPACK"}
    logger = get_logger("dhcp_server")
    with ws.open_socket(67) as socket:
        logger.debug("DHCP server open for business")
        while True:
            # On reception of server discovery and address request packets, send the corresponding response.
            packet_client = socket.recv()
            type_msg = packet_client.payload.entries[PayloadDictionaryType.CONTENT]
            if type_msg not in responses:
                msg = f"Received unknown message {repr(type_msg)} from {packet_client.source.hostname} -- DROP"
                logger.warning(msg)
            else:
                logger.info(f"Received {type_msg} from {packet_client.source.hostname}")
                socket.send(packet_client.source, next(size_packet_dhcp), dhcp_payload(responses[type_msg]))


# Used by both mDNS and LLMNR responders.
size_packet_dns = num_bytes(expo(192.0 * B), header=68 * B, upper=576 * B)


def mdns_daemon(ws: Workstation) -> None:
    # This models only mDNS local hostname name resolution; service discovery is TBD.
    local.name = f"{ws.name} / mDNS responder"
    logger = get_logger("mdns_responder")
    while True:
        queries = []
        try:
            with ws.open_socket(5353) as socket:
                while True:
                    with ws.awake():
                        packet = socket.recv()
                    pl_ent = packet.payload.entries
                    logger.debug(f"Received message {pl_ent} from {packet.source}")
                    content_resolve = pl_ent[PayloadDictionaryType.CONTENT] == "resolve"
                    hostname_match = pl_ent[PayloadDictionaryType.HOSTNAME] == ws.name
                    if pl_ent[PayloadDictionaryType.CONTENT] == "query":
                        queries.append(packet)
                        socket.broadcast(
                            5353,
                            len(packet),
                            Payload({PayloadDictionaryType.CONTENT: "resolve",
                                     PayloadDictionaryType.HOSTNAME: pl_ent[PayloadDictionaryType.HOSTNAME]})
                        )  # FIXME -- add port info

                    elif pl_ent[PayloadDictionaryType.CONTENT] == "iam":
                        i_del = None
                        for i, packet_query in enumerate(queries):
                            if packet_query.payload.entries[PayloadDictionaryType.HOSTNAME] \
                               == pl_ent[PayloadDictionaryType.HOSTNAME]:
                                i_del = i
                                socket.send(packet_query.source, len(packet), packet.payload)
                                break
                        if i_del is not None:
                            del queries[i_del]

                    elif content_resolve and hostname_match:
                        logger.info(f"Resolve hostname {ws.name} as {ws.address_default}")
                        socket.broadcast(
                            5353,
                            next(size_packet_dns),
                            Payload({PayloadDictionaryType.CONTENT: "iam",
                                     PayloadDictionaryType.HOSTNAME: ws.name,
                                     PayloadDictionaryType.ADDRESS: ws.address_default})
                        )  # FIXME

        except Workstation.FellAsleep:
            # This mechanism encodes the inevitable drop of packets and loss of socket inherent to wake-cycling the
            # workstation.
            logger.debug("Reset by workstation falling asleep")


def llmnr_daemon(ws: Workstation) -> None:
    local.name = f"{ws.name} / LLMNR responder"
    logger = get_logger("llmnr_responder")
    while True:
        try:
            with ws.open_socket(5355) as socket:
                while True:
                    with ws.awake():
                        packet = socket.recv()
                    payload_entries = packet.payload.entries
                    if payload_entries[PayloadDictionaryType.CONTENT] == "resolve" and \
                       payload_entries[PayloadDictionaryType.HOSTNAME] == ws.name:
                        logger.info(f"Resolve hostname {ws.name} as {ws.address_default}")
                        socket.send(
                            packet.source,
                            next(size_packet_dns),
                            Payload({PayloadDictionaryType.CONTENT: "iam",
                                     PayloadDictionaryType.HOSTNAME: ws.name,
                                     PayloadDictionaryType.ADDRESS: ws.address_default})
                        )
        except Workstation.FellAsleep:
            logger.debug("LLMNR Reset by workstation falling asleep")


delay_identity_queries = expo(2.0 * MIN)
size_packet_delta = normal(0.0 * B, 10.0 * B)


@contextmanager
def _query(protocol: str, logger: logging.Logger, ws: Workstation, size_packet_base: int, payload: Payload):
    try:
        local.name = f"{protocol} query from {ws.name}"
        with ws.open_socket() as socket:
            yield (socket, int(size_packet_base + next(size_packet_delta)))
            try:
                with ws.awake(), ws.timeout(5.0):  # FIXME - fugly
                    response = socket.recv()
                    rpl = response.payload.entries
                    logger.info("%s resolved to %s" %
                                (rpl[PayloadDictionaryType.HOSTNAME],
                                 rpl[PayloadDictionaryType.ADDRESS]))
            except Workstation.Timeout:
                logger.debug(f"Resolution of {payload.entries[PayloadDictionaryType.HOSTNAME]} timed out")
    except Workstation.FellAsleep:
        logger.debug("Resolution of %s killed by workstation falling asleep" %
                     payload.entries[PayloadDictionaryType.HOSTNAME])


def _query_mdns(logger: logging.Logger, ws: Workstation, size_packet_base: int, payload: Payload):
    with _query("mDNS", logger, ws, size_packet_base, payload) as (socket, size_packet):
        socket.send(Location(ws.address_default, 5353), size_packet, payload)


def _query_llmnr(logger: logging.Logger, ws: Workstation, size_packet_base: int, payload: Payload):
    with _query("LLMNR", logger, ws, size_packet_base, payload) as (socket, size_packet):
        socket.broadcast(5355, size_packet, payload)


def client_activity(ws: Workstation, name_next_query: VarRandom[str]) -> None:
    local.name = f"{ws.name} / Client activity"
    logger = get_logger("client_activity")
    while True:
        ws.wait_until_awake(logger)  # FIXME
        try:
            with ws.awake():
                advance(next(delay_identity_queries))

            while True:
                target_query = next(name_next_query)
                if target_query != ws.name:
                    break

            logger.info(f"Query IP address of {target_query}")

            size_packet_base = next(size_packet_dns)
            add(_query_mdns, logger, ws, size_packet_base, Payload({PayloadDictionaryType.CONTENT: "query",
                                                                    PayloadDictionaryType.HOSTNAME: target_query}))
            add(_query_llmnr, logger, ws, size_packet_base, Payload({PayloadDictionaryType.CONTENT: "resolve",
                                                                     PayloadDictionaryType.HOSTNAME: target_query}))
        except Workstation.FellAsleep:
            logger.debug("Reset by machine falling asleep")


net_local = None


def init():
    global net_local

    parser = argparse.ArgumentParser(description="Simulator of the baseline behaviour of a simple flat network.")
    parser.add_argument("-c", "--cidr", help="CIDR prefix describing basic network setup.", default="192.168.4.0/24")
    parser.add_argument("-n", "--num-endpoints", help="Number of endpoints into the simulation.", type=int)
    parser.add_argument("-v", "--verbose", help="Log debugging information.", action="store_true", default=False)
    parser.add_argument("-d", "--duration", help="Duration (in hours) of simulation.", type=float, default=12 * H)
    parser.add_argument("-o", "--colors-off", help="Turn off colored output,", action="store_true", default=False)
    args = parser.parse_args()

    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO, handlers=[])
    h = logging.StreamHandler(sys.stdout)
    h.setFormatter(logging.Formatter("<%(levelname)s> -- %(message)s"))
    logger = logging.getLogger("main")
    logger.addHandler(h)

    if args.duration <= 0.0:
        logger.critical("Suggested simulation duration {args.duration} makes no sense. Abort.")

    sim = Simulator()
    num_addresses = ip_network(args.cidr).num_addresses - NUM_ADDRESSES_RESERVED
    if num_addresses < MIN_NUM_ENDPOINTS:
        logger.critical(f"Unsuitable CIDR prefix for simulating a non-trivial network: {args.cidr} -- Abort.")
        sys.exit(1)

    logger.debug(f"CIDR prefix of network: {args.cidr}")
    net_local = Network(
        sim,
        cidr=args.cidr,
        bandwidth=constant(1 * GbPS),
        latency=normal(5 * MS, 1 * MS)
    )

    # Create a router. Currently used in malware_sample
    router = Endpoint("Router", net_local)

    if args.num_endpoints is None:
        num_endpoints = max(MIN_NUM_ENDPOINTS, int(0.2 * num_addresses))
    else:
        num_endpoints = args.num_endpoints
        if num_endpoints < MIN_NUM_ENDPOINTS:
            logger.warning(
                f"Requested number of endpoints ({num_endpoints}) is insufficient; " +  # noqa: W504
                f"raising it to {MIN_NUM_ENDPOINTS}."
            )
            num_endpoints = MIN_NUM_ENDPOINTS

    num_workstations = num_endpoints - 1  # DHCP server is not a workstation.
    num_mdns = int(0.9 * num_workstations)
    num_llmnr = num_workstations - num_mdns
    logger.debug(
        f"Setting up 1 DHCP server and {num_workstations} workstations -- {num_mdns} / mDNS, {num_llmnr} / LLMNR."
    )

    dhcp_server = Endpoint("DHCPServer", net_local)
    dhcp_server.install(dhcp_serve)

    ws_list = []
    names_ws = []
    name_next_query = distribution(names_ws)

    for n in range(num_workstations):
        name = f"Workstation-{n+1}"
        names_ws.append(name)

        ws = Workstation(name, net_local)
        ws.install(workstation_blinking)
        ws.install(client_activity, name_next_query)
        if n <= num_mdns:
            ws.install(mdns_daemon)
        else:
            ws.install(llmnr_daemon)

        ws_list.append(ws)

    return sim, args.duration, ws_list, router, (not args.colors_off)


if __name__ == '__main__':
    sim, dur, _, _, _ = init()
    sim.run(dur)
