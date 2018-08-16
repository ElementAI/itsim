from collections import OrderedDict
from contextlib import contextmanager
from typing import cast, MutableMapping, List, Union, Tuple, ContextManager

from greensim import Process
from itsim import AddressRepr, Address, CidrRepr, as_address, Port, PortRepr
from itsim.network import Packet, Network, InvalidAddress, AddressError


MapPorts = MutableMapping[Port, Process]


class AddressHasPortsOpen(AddressError):

    def __init__(self, address: Address, ports: List[Port]):
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
            if not port in self.ports:
                return port


class Node(object):

    LocationBind = Union[None, AddressRepr, PortRepr, Location, Tuple]

    def __init__(self):
        super().__init__()
        self._networks: MutableMapping[Address, _NetworkLink] = OrderedDict()

    def link_to(self, network: Network, ar: AddressRepr = None, *forward_me: CidrRepr) -> "Node":
        if as_address(ar) not in self._networks:
            address = network.link(self, ar, *forward_me)
            self._networks[address] = _NetworkLink(network)
        return self

    def unlink_from(self, ar: AddressRepr) -> "Node":
        address = as_address(ar)
        if address in self._networks:
            if len(self._networks[address].ports) > 0:
                raise AddressHasPortsOpen(address, list(self._networks[address].ports.keys()))
            self._networks[address].unlink(ar)
            del self._networks[address]
        return self

    @property
    def addresses(self):
        return self._networks.keys()

    @property
    def address_default(self) -> Address:
        try:
            return next(self._networks.keys())
        except StopIteration:
            raise NoNetworkLinked()

    def _as_location(lb: Node.LocationBind):
        if lb is None:
            return self._as_location(Location(None, None))
        elif isinstance(lb, int):
            return self._as_location(Location(None, cast(Port, lb)))
        elif isinstance(lb, AddressRepr):
            return self._as_location(Location(cast(AddressRepr, lb), 0))
        elif isinstance(lb, Tuple):
            return self._as_location(Location(lb[0], lb[1]))
        elif isinstance(lb, Location):
            loc = cast(Location, lb)
            address: Address = loc.host
            if not isinstance(loc.host, Address):
                raise InvalidAddress(loc.host)
            elif loc.host == as_address(0):
                address = self.address_default
            else loc.host not in self.addresses:
                raise InvalidAddress(loc.host)

            port: Port = loc.port
            if port == 0:
                port = self._networks[address].get_port_free()

            return Location(address, port)

    @contextmanager
    def bind(self, lb: Node.LocationBind = None) -> ContextManager[Socket]:
        loc = self._as_location(lb)
        self._networks[loc.host].ports[loc.port] = Process.current()
        yield loc
        del self._networks[loc.host].ports[loc.port]

    def receive(self, packet: Packet) -> None:
        raise NotImplemented()


class Socket(object):

    def __init__(self, source: Location, network: Network) -> None:
        super().__init__()
        self._source = source
        self._network = network

    def send(self, destination: Location, num_bytes: int) -> None:
        raise NotImplemented()

    def recv(self) -> Packet:
        raise NotImplemented()


class UDP(object):
