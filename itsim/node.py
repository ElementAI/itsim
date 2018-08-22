from collections import OrderedDict
from contextlib import contextmanager
from ipaddress import _BaseAddress
from itertools import cycle
from typing import cast, Any, MutableMapping, List, Union, Tuple, Iterable, Generator, Optional

from greensim import Process
from itsim import AddressRepr, Address, CidrRepr, as_address, Port, PortRepr, Location, _Node
from itsim.network import Packet, Network, InvalidAddress, AddressError, AddressInUse


MapPorts = MutableMapping[Port, Process]


class AddressHasPortsOpen(AddressError):

    def __init__(self, address: Any, ports: List[Port]) -> None:
        super.__init__(address)
        self.ports = ports


class NoNetworkLinked(Exception):
    pass


class TooManyPorts(AddressError):
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


class Socket(object):

    def __init__(self, source: Location, network: Network) -> None:
        super().__init__()
        self._source = source
        self._network = network

    def send(self, destination: Location, num_bytes: int) -> None:
        raise NotImplemented()

    def recv(self) -> Packet:
        raise NotImplemented()


class Node(_Node):

    LocationBind = Union[None, AddressRepr, PortRepr, Location, Tuple]

    def __init__(self):
        super().__init__()
        self._networks: MutableMapping[Address, _NetworkLink] = OrderedDict()
        self._address_default: Optional[Address] = None

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

    def _as_location(self, lb: "Node.LocationBind"):
        if lb is None:
            return self._as_location(Location(None, None))
        elif isinstance(lb, int):
            return self._as_location(Location(None, cast(Port, lb)))
        elif isinstance(lb, (type(None), str, _BaseAddress)):
            return self._as_location(Location(cast(AddressRepr, lb), 0))
        elif isinstance(lb, tuple):
            return self._as_location(Location(lb[0], lb[1]))
        elif isinstance(lb, Location):
            loc = cast(Location, lb)
            if not isinstance(loc.host, _BaseAddress):
                raise InvalidAddress(loc.host)
            elif loc.host == as_address(0):
                address = self.address_default
            elif loc.host not in self.addresses:
                raise InvalidAddress(loc.host)

            port: Port = loc.port
            if port == 0:
                port = self._networks[address].get_port_free()

            return Location(address, port)

    @contextmanager
    def bind(self, lb: "Node.LocationBind" = None) -> Generator[Socket, None, None]:
        loc = self._as_location(lb)
        self._networks[loc.host].ports[loc.port] = Process.current()
        yield loc
        del self._networks[loc.host].ports[loc.port]

    def receive(self, packet: Packet) -> None:
        raise NotImplemented()


class _DefaultAddressSetter(object):

    def __init__(self, node: Node, address: Address) -> None:
        super().__init__()
        self._node = node
        self._address = address

    def set_default(self) -> None:
        self._node._address_default = self._address


# class UDP(object):


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
