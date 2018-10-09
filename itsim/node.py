from collections import OrderedDict
from contextlib import contextmanager
from ipaddress import _BaseAddress
from itertools import cycle
from queue import Queue
from typing import Any, cast, Generator, Iterable, Optional, MutableMapping, List, Tuple, Union

from greensim import Process, Signal

from itsim import _Node
from itsim.it_objects import ITObject
from itsim.it_objects.location import Location
from itsim.it_objects.networking import _Link
from itsim.it_objects.networking.link import AddressError, AddressInUse, InvalidAddress
from itsim.it_objects.payload import Payload
from itsim.it_objects.packet import Packet
from itsim.network import Network
from itsim.types import AddressRepr, Address, CidrRepr, as_address, Port, PortRepr


MapPorts = MutableMapping[Port, Process]


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


class _NetworkLink(object):

    def __init__(self, address: Address, network: Network) -> None:
        super().__init__()
        self.address = address
        self.network = network
        self.ports: MapPorts = OrderedDict()
        self._seq_ports_unprivileged = cycle(range(1024, 65536))

    def get_port_free(self):
        if len(self.ports) >= 60000:
            raise TooManyPorts(self.address)
        for port in self._seq_ports_unprivileged:
            if port not in self.ports:
                return port

    def sever(self) -> None:
        self.network.unlink(self.address)


class Socket(ITObject):

    def __init__(self, src: Location, node: _Node) -> None:
        super().__init__()
        self._src = src
        self._node = node
        self._packet_queue: Queue[Packet] = Queue()
        self._packet_signal: Signal = Signal()
        self._packet_signal.turn_off()

    def send(self, dest: Location, byte_size: int, payload: Payload) -> None:
        self._node._send_to_network(Packet(self._src, dest, byte_size, payload))

    def broadcast(self, port: int, byte_size: int, payload: Payload) -> None:
        dest_addr = self._node._get_network_broadcast_address(self._src.host)
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
        if self._packet_queue.empty():
            self._packet_signal.turn_off()
        return output


class Node(_Node):

    LocationBind = Union[None, AddressRepr, PortRepr, Location, Tuple]

    def __init__(self):
        super().__init__()
        self._networks: MutableMapping[Address, _NetworkLink] = OrderedDict()
        self._address_default: Optional[Address] = None
        self._sockets: MutableMapping[Location, Socket] = OrderedDict()
        self._links: MutableMapping[AddressRepr, _Link] = set()

    def add_physical_link(self, link: _Link, ar: AddressRepr) -> None:
        link.add_node(self, ar)
        self._links[ar] = link

    def remove_physical_links(self, link: _Link, ar: AddressRepr) -> bool:
        if ar not in self._links:
            return False
        del self._links[ar]
        return link.drop_node(ar)

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

    def _as_location(self, lb: "Node.LocationBind") -> Location:
        if lb is None:
            return Location(self.address_default, 0)
        elif isinstance(lb, int):
            return Location(self.address_default, cast(Port, lb))
        elif isinstance(lb, (str, _BaseAddress)):
            return Location(cast(AddressRepr, lb), 0)
        elif isinstance(lb, tuple):
            return Location(lb[0], lb[1])
        elif isinstance(lb, Location):
            return cast(Location, lb)
        raise ValueError("What is that LocationBind instance?")

    def _as_source_bind(self, lb: "Node.LocationBind") -> Location:
        loc = self._as_location(lb)

        # Address here must be one of the node's addresses.
        if not isinstance(loc.host, _BaseAddress) or loc.host not in self.addresses:
            raise InvalidAddress(loc.host)
        elif loc.host not in self.addresses:
            raise InvalidAddress(loc.host)
        else:
            address = loc.host

        port: Port = loc.port
        if port == 0:
            # TODO -- Disambiguate between address 0 (bind all addresses against the port) and a specific binding.
            port = self._networks[address].get_port_free()

        return Location(address, port)

    @contextmanager
    def bind(self, lb: "Node.LocationBind" = None) -> Generator[Location, None, None]:
        src = self._as_source_bind(lb)
        if src.port in self._networks[src.host_as_address()].ports.keys():
            raise PortAlreadyInUse()

        self._networks[src.host_as_address()].ports[src.port] = Process.current()
        try:
            yield src
        finally:
            del self._networks[src.host_as_address()].ports[src.port]

    @contextmanager
    def open_socket(self, lb: "Node.LocationBind" = None) -> Generator[Socket, None, None]:

        with self.bind(lb) as src:
            sock = Socket(src, self)

            # Listen on the broadcast address
            broadcast_addr = self._get_network_broadcast_address(src.host_as_address())
            broadcast = Location(broadcast_addr, src.port)

            self._sockets[src] = sock
            self._sockets[broadcast] = sock
            try:
                yield sock
            finally:
                del self._sockets[src]
                del self._sockets[broadcast]

    def _send_to_network(self, packet: Packet) -> None:
        src = packet.source
        if src.host_as_address() not in self._networks or \
           src.port not in self._networks[src.host_as_address()].ports.keys():
            raise NoNetworkLinked()
        network = self._networks[src.host_as_address()].network
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


class Router(Node):

    def __init__(self, lan: Network, wan: Network) -> None:
        super().__init__()
        raise NotImplementedError()
