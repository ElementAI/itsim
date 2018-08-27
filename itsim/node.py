from collections import OrderedDict
from contextlib import contextmanager
from ipaddress import _BaseAddress
from itertools import cycle
from queue import Queue
from typing import cast, Any, MutableMapping, List, Union, Tuple, Iterable, Generator, Optional

from greensim import Process

from itsim import _Node
from itsim.it_objects import ITObject
from itsim.it_objects.location import Location
from itsim.it_objects.payload import Payload
from itsim.it_objects.packet import Packet
from itsim.network import Network, InvalidAddress, AddressError, AddressInUse
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


class SocketAlreadyOpen(Exception):
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

    def __init__(self, src: Location, dest: Location, node: _Node) -> None:
        super().__init__()
        self._src = src
        self._dest = dest
        self._node = node
        self._payload_queue: Queue[Payload] = Queue()

    def send(self, payload: Payload, byte_size: int) -> None:
        self._node.send_to_network(Packet(self._src, self._dest, byte_size, payload))

    def enqueue(self, payload: Payload) -> None:
        self._payload_queue.put(payload)

    def recv(self) -> Optional[Payload]:
        if self._payload_queue.empty():
            return None
        else:
            return self._payload_queue.get()


class Node(_Node):

    LocationBind = Union[None, AddressRepr, PortRepr, Location, Tuple]

    def __init__(self):
        super().__init__()
        self._networks: MutableMapping[Address, _NetworkLink] = OrderedDict()
        self._address_default: Optional[Address] = None
        self._sockets: MutableMapping[Location, Socket] = OrderedDict()

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
            return Location(0, 0)
        elif isinstance(lb, int):
            return Location(None, cast(Port, lb))
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
        if src.port in self._networks[src.host_as_address()].ports:
            raise PortAlreadyInUse()
        self._networks[src.host_as_address()].ports[src.port] = Process.current()
        yield src
        del self._networks[src.host_as_address()].ports[src.port]

    @contextmanager
    def open_socket(self, src: Location, dest: Location) -> Generator[Socket, None, None]:
        if self._sockets[src] is not None:
            raise SocketAlreadyOpen()
        sock = Socket(src, dest, self)
        self._sockets[src] = sock
        yield sock
        del self._sockets[src]

    def send_to_network(self, packet: Packet) -> None:
        src = packet.source
        network = self._networks[src.host_as_address()].network
        network.transmit(packet)

    def receive(self, packet: Packet) -> None:
        dest = packet.dest
        if self._sockets[dest] is not None:
            self._sockets[dest].enqueue(packet.payload)


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


class Endpoint(Node):

    def __init__(self, name: str, network: Network) -> None:
        super().__init__()
        raise NotImplementedError()

    def install(self, *fn_software):
        raise NotImplementedError()
        return self
