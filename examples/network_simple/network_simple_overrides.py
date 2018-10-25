from collections import OrderedDict
from contextlib import contextmanager

import greensim
from greensim import advance
from greensim.logging import Filter
from greensim.random import bounded, expo, VarRandom

from ipaddress import _BaseAddress

from itertools import cycle, dropwhile

from itsim import ITObject
from itsim.simulator import Simulator
from itsim.network import AddressError, AddressInUse, InvalidAddress, Location, Link, \
    Packet, Payload, PayloadDictionaryType
from itsim.node import Node as ParentNode, Socket as ParentSocket
from itsim.types import Address, AddressRepr, as_address, as_cidr, Cidr, CidrRepr, Port, PortRepr
from itsim.units import MbPS, MS, S

import json

import logging

from numbers import Real

from queue import Queue

import sys

from typing import Any, Callable, cast, Generator, Iterable, Iterator, List, MutableMapping, Optional, Tuple, TypeVar


class AddressHasPortsOpen(AddressError):

    def __init__(self, address: Any, ports: List[Port]) -> None:
        super.__init__(address)
        self.ports = ports


class NoNetworkLinked(Exception):
    pass


class TooManyPorts(AddressError):
    pass


class PortAlreadyInUse(Exception):
    pass


class _Node(ParentNode):
    def _send_to_network():
        pass


class Socket(ParentSocket):

    def __init__(self, src: Location, node: _Node) -> None:
        super().__init__(src, node)
        self._src = src
        self._node = node
        self._packet_queue: Queue[Packet] = Queue()
        self._packet_signal: greensim.Signal = greensim.Signal()
        self._packet_signal.turn_off()
        # Keeps track of packets waiting for responses so they can be logged together
        # The float keeps track of the time that the packet was queued up
        # This is not at all the best way to handle this, but as a quick hack it is effective
        self._outbound_packets: MutableMapping[Location, Tuple[Packet, float]] = OrderedDict()
        self._inbound_packets: MutableMapping[Location, Tuple[Packet, float]] = OrderedDict()

    def get_logger(self, name_logger=__name__):
        logger = logging.getLogger(name_logger)
        if len(logger.handlers) == 0:
            logger.setLevel(logging.getLogger().level)
            logger.addFilter(Filter())
            handler = logging.StreamHandler(sys.stdout)
            handler.setFormatter(
                logging.Formatter("JSON-OUT <%(levelname)s> %(sim_time)f [%(sim_process)s] %(message)s"))
            logger.addHandler(handler)
        return logger

    # Designed to keep this hack contained. This allows unit tests without a Simulation to succeed
    def get_time_with_fallback(self):
        try:
            return greensim.now()
        except TypeError:
            return 0

    # Check to see if this packet is in response to another one. If so, log the pair as Inbound
    # If not, check whether this socket is already waiting for a response from the destination host
    # If it is waiting just log the old packet without a response, assuming all new responses are to the latest packet
    # If it is not waiting, queue up the outbound packet so we can log the response together with it
    def correlate_outbound_packet(self, dest: Location, ob_packet: Packet) -> None:
        if dest in self._inbound_packets:
            self.log_pair(self._inbound_packets[dest][0], ob_packet, self._inbound_packets[dest][1], True)
            del self._inbound_packets[dest]
        else:
            if dest in self._outbound_packets:
                self.log_pair(None, self._outbound_packets[dest][0], self._outbound_packets[dest][1], False)
            self._outbound_packets[dest] = (ob_packet, self.get_time_with_fallback())

    # Check to see if this packet is in response to another one. If so, log the pair as Outbound
    # If not, queue up the inbound packet so we can log the response together with it
    # This method is used so that the socket can remain independent of packet creation
    # And also so the hack is contained here in this class
    def correlate_inbound_packet(self, src: Location, ib_packet: Packet) -> None:
        if src in self._outbound_packets:
            self.log_pair(ib_packet, self._outbound_packets[src][0], self._outbound_packets[src][1], False)
            del self._outbound_packets[src]
        else:
            self._inbound_packets[src] = (ib_packet, self.get_time_with_fallback())

    def send(self, dest: Location, byte_size: int, payload: Payload) -> None:
        ob_packet = Packet(self._src, dest, byte_size, payload)
        self._node._send_to_network(ob_packet)
        self.correlate_outbound_packet(dest, ob_packet)

    def broadcast(self, port: int, byte_size: int, payload: Payload) -> None:
        dest_addr = self._node._get_network_broadcast_address(self._src.hostname)
        self.send(Location(dest_addr, port), byte_size, payload)

    def _enqueue(self, packet: Packet) -> None:
        self._packet_queue.put(packet)
        self._packet_signal.turn_on()

    def recv(self) -> Packet:
        # Waiting loop
        while self._packet_queue.empty():
            self._packet_signal.wait()

        # Make sure to update the Signal in case more Processes are in the Signal's queue
        output = self._packet_queue.get()

        self.correlate_inbound_packet(output.source, output)

        if self._packet_queue.empty():
            self._packet_signal.turn_off()
        return output

    # Take 0 - 2 packets and log whatever information is available as a JSON object in the format
    # defined in the Telemetry table
    # This method is just a stand-in so it is not very intelligent
    def log_pair(self,
                 packet_in: Optional[Packet],
                 packet_out: Optional[Packet],
                 start: float,
                 is_inbound: bool) -> None:
        remote_ip = "0"
        if packet_out is not None:
            if PayloadDictionaryType.ADDRESS in packet_out._payload._entries:
                remote_ip = str(cast(Address,
                                     packet_out._payload._entries[PayloadDictionaryType.ADDRESS]))
            else:
                remote_ip = str(packet_out.dest.hostname)

        self.get_logger().info(json.dumps({"Connection_Type": "UDP",
                                           "Local_IP": 0 if packet_in is None else str(packet_in.dest.hostname),
                                           "Local_Port": 0 if packet_in is None else str(packet_in.dest.port),
                                           "Direction": "Inbound" if is_inbound else "Outbound",
                                           "Remote_IP": remote_ip,
                                           "Remote_Port": 0 if packet_out is None else str(packet_out.dest.port),
                                           "Sent_Bytes": 0 if packet_out is None else str(packet_out.byte_size),
                                           "Received_Bytes": 0 if packet_in is None else str(packet_in.byte_size),
                                           "PID": 0,
                                           "Start_Time": start,
                                           "End_Time": self.get_time_with_fallback(),
                                           "Parent_Process_Path": "/home/town",
                                           "Parent_Process_Start_Time": start}))

    # When the socket is closed this method is called to log whatever packets didn't end up
    # being part of a transaction
    def flush_logs(self) -> None:
        for pair in self._outbound_packets.values():
            self.log_pair(None, pair[0], pair[1], False)

        for pair in self._inbound_packets.values():
            self.log_pair(pair[0], None, pair[1], True)


class Network(ITObject):

    def __init__(
        self,
        sim: Simulator,
        cidr: CidrRepr,
        latency: VarRandom[Real],
        bandwidth: VarRandom[Real],
        num_skip_addresses: int = 0
    ) -> None:
        super().__init__()
        self._sim = sim
        self._cidr = as_cidr(cidr)
        self._latency = bounded(latency, lower=0)
        self._bandwidth = bounded(bandwidth, lower=0.125)  # 1 bit / s  X-O
        self._nodes: MutableMapping[Address, _Node] = OrderedDict()
        self._forwarders: MutableMapping[Cidr, _Node] = OrderedDict()
        self._addresses_free: List[Address] = []
        self._top_free: Iterator[Address] = (
            addr
            for _, addr in dropwhile(
                lambda p: p[0] < num_skip_addresses,
                enumerate(self.cidr.hosts())
            )
        )

    @property
    def cidr(self) -> Cidr:
        return self._cidr

    @property
    def sim(self) -> Simulator:
        return self._sim

    def link(self, node: _Node, ar: AddressRepr = None, *forward_to: CidrRepr) -> Address:
        """
        Adds the given node to the network. If a certain address is requested for it, the node is given this address,
        unless it's already in use. Furthermore, any number of CIDR prefixes can be provided, which will instruct the
        network to forward to the given node any non-local packet that CIDR-match these prefixes.

        If a forwarding to a certain CIDR prefix was already set up, the latest call to link() overrides any previous
        call: the latest forwarding to a CIDR prefix is in action, and no warning is given of the override.
        """
        if ar is None:
            address = self._get_address_free()
        else:
            address = as_address(ar)

        if address not in self._cidr:
            raise InvalidAddress(address)
        if address in self._nodes:
            raise AddressInUse(address)

        self._nodes[address] = node
        if forward_to is not None:
            for cidr in (as_cidr(c) for c in forward_to):
                self._forwarders[cidr] = node

        return address

    def unlink(self, ar: AddressRepr) -> None:
        address = as_address(ar)
        if address in self._nodes:
            for cidr, node in self._forwarders.items():
                if address in node.addresses:
                    del self._forwarders[cidr]
            del self._nodes[address]
            self._addresses_free.append(address)

    def _get_address_free(self) -> Address:
        try:
            return cast(Address, next(self._top_free))
        except StopIteration:
            if len(self._addresses_free) > 0:
                address = self._addresses_free[0]
                del self._addresses_free[0]
                return address
            else:
                raise NetworkFull()

    @property
    def address_broadcast(self) -> Address:
        return self._cidr.broadcast_address

    def transmit(self, packet: Packet, receiver_maybe: Optional[_Node] = None) -> None:
        if not isinstance(packet.dest.hostname, _BaseAddress):
            raise InvalidAddress(packet.dest.hostname)

        receivers: Iterable[_Node]
        if receiver_maybe is not None:
            receivers = [cast(_Node, receiver_maybe)]
        elif packet.dest.hostname == self.address_broadcast:
            receivers = self._nodes.values()
        elif packet.dest.hostname in self._nodes:
            receivers = [self._nodes[packet.dest.hostname_as_address()]]
        else:
            receivers = [self._get_forwarder(cast(Address, packet.dest.hostname))]

        def transmission():
            advance(next(self._latency) + len(packet) / next(self._bandwidth))
            for node in receivers:
                self.sim.add(node._receive, packet)
        self.sim.add(transmission)

    def _get_forwarder(self, dest: Address) -> _Node:
        candidates = [(cidr, node) for cidr, node in self._forwarders.items() if dest in cidr]
        if len(candidates) == 0:
            raise CannotForward(dest)
        return max(candidates, key=lambda cidr_node: cidr_node[0])[1]


class Node(_Node):

    LocationBind = TypeVar("LocationBind", AddressRepr, PortRepr, Location, Tuple)

    def __init__(self):
        super().__init__()
        self._networks: MutableMapping[Address, _NetworkLink] = OrderedDict()
        self._address_default: Optional[Address] = None
        self._sockets: MutableMapping[Location, Socket] = OrderedDict()
        self._links: MutableMapping[AddressRepr, Link] = OrderedDict()

    def link_to(self, network: Network, ar: AddressRepr = None, *forward_me: CidrRepr) -> "_DefaultAddressSetter":
        if as_address(ar) in self._networks:
            raise AddressInUse(ar)
        address = network.link(self, ar, *forward_me)
        self._networks[address] = _NetworkLink(address, network)
        return _DefaultAddressSetter(self, address)

    def unlink_from(self, ar: AddressRepr) -> None:
        address = as_address(ar)
        if address in self._networks:
            if len(self._networks[address].ports) > 0:
                raise AddressHasPortsOpen(address, list(self._networks[address].ports.keys()))
            self._networks[address].sever()
            del self._networks[address]

    @property
    def addresses(self) -> Iterable[Address]:
        return self._networks.keys()

    @property
    def address_default(self) -> Address:
        try:
            return next(iter(self._networks.keys()))
        except StopIteration:
            raise NoNetworkLinked()

    @contextmanager
    def bind(self, lb: Optional[LocationBind] = None) -> Generator[Location, None, None]:
        src = self._as_source_bind(lb)  # type: ignore

        if src.port == 0:
            src = Location(src.hostname, self._networks[src.hostname].get_port_free())

        if src.port in self._networks[src.hostname_as_address()].ports.keys():
            raise PortAlreadyInUse()

        self._networks[src.hostname_as_address()].ports[src.port] = greensim.Process.current()
        try:
            yield src
        finally:
            del self._networks[src.hostname_as_address()].ports[src.port]

    @contextmanager
    def open_socket(self, lb: Optional[LocationBind] = None) -> Generator[Socket, None, None]:
        with self.bind(lb) as src:  # type: ignore
            sock = Socket(src, self)

            # Listen on the broadcast address
            broadcast_addr = self._get_network_broadcast_address(src.hostname_as_address())
            broadcast = Location(broadcast_addr, src.port)

            self._sockets[src] = sock
            self._sockets[broadcast] = sock
            try:
                yield sock
            finally:
                sock.flush_logs()
                del self._sockets[src]
                del self._sockets[broadcast]

    def _send_to_network(self, packet: Packet) -> None:
        src = packet.source
        if src.hostname_as_address() not in self._networks or \
           src.port not in self._networks[src.hostname_as_address()].ports.keys():
            raise NoNetworkLinked()
        network = self._networks[src.hostname_as_address()].network
        network.transmit(packet)

    def _receive(self, packet: Packet) -> None:
        dest = packet.dest
        if dest in self._sockets.keys():
            self._sockets[dest]._enqueue(packet)

    def _get_network_broadcast_address(self, src_addr: Address) -> Address:
        if src_addr not in self._networks:
            raise NoNetworkLinked()
        network = self._networks[src_addr].network
        return network.address_broadcast


class _DefaultAddressSetter(object):

    def __init__(self, node: Node, address: Address) -> None:
        super().__init__()
        self._node = node
        self._address = address

    def set_default(self) -> None:
        self._node._address_default = self._address


class Endpoint(Node):

    def __init__(self, name: str, network: Network, ar: AddressRepr = None, *forward_to: CidrRepr) -> None:
        super().__init__()
        self._name = name
        self._network = network
        self._sim = network.sim
        self.link_to(network, ar, *forward_to)

    @property
    def network(self) -> Network:
        return self._network

    @property
    def name(self) -> str:
        return self._name

    @property
    def sim(self) -> Simulator:
        return self._sim

    def install(self, fn_software: Callable, *args: Any, **kwargs: Any) -> None:
        self._sim.add(fn_software, self, *args, **kwargs)

    def install_in(self, delay: float, fn_software: Callable, *args: Any, **kwargs: Any) -> None:
        self._sim.add_in(delay, fn_software, self, *args, **kwargs)

    def install_at(self, moment: float, fn_software: Callable, *args: Any, **kwargs: Any) -> None:
        self._sim.add_at(moment, fn_software, self, *args, **kwargs)

# === WARNING -- The following code is deprecated and will be replaced presently. ===


class NetworkFull(Exception):
    pass


class CannotForward(AddressError):
    pass


class Internet(Network):

    def __init__(
        self,
        sim: Simulator,
        latency: Optional[VarRandom[Real]] = None,
        bandwidth: Optional[VarRandom[Real]] = None
    ) -> None:
        super().__init__(
            sim,
            cidr="0.0.0.0/0",
            latency=latency or bounded(expo(1 * S), lower=20 * MS),
            bandwidth=bandwidth or expo(10 * MbPS)
        )

    def add_receiver(self, loc: Location, receiver: Callable[[Packet], None]) -> None:
        raise NotImplementedError("Stub")


class _NetworkLink(object):

    def __init__(self, address: Address, network: Network) -> None:
        super().__init__()
        self.address = address
        self.network = network
        self.ports = OrderedDict()
        self._seq_ports_unprivileged = cycle(range(1024, 65536))

    def get_port_free(self):
        if len(self.ports) >= 60000:
            raise TooManyPorts(self.address)
        for port in self._seq_ports_unprivileged:
            if port not in self.ports:
                return port

    def sever(self) -> None:
        self.network.unlink(self.address)
