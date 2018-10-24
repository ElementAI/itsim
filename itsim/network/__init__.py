from collections import OrderedDict
from enum import Enum, unique
from functools import total_ordering
from ipaddress import _BaseAddress
from itertools import dropwhile
from numbers import Real
from typing import cast, MutableMapping, List, Iterable, Iterator, Optional, Callable, Dict, Any

from greensim import advance
from greensim.random import VarRandom, bounded, expo

from itsim import _Node, _Packet, ITObject
from itsim.network.service import Service
from itsim.random import VarRandomTime, VarRandomBandwidth
from itsim.simulator import Simulator
from itsim.types import CidrRepr, Cidr, as_cidr, Address, AddressRepr, as_address, HostnameRepr, PortRepr, \
    as_hostname, as_port, Hostname, Port
from itsim.units import MS, S, MbPS


class AddressError(Exception):
    """
    Generic superclass for Exception objects that refer to an issue with a specific address
    """

    def __init__(self, value: Any) -> None:
        super().__init__()
        self.value_for_address = value


class AddressInUse(AddressError):
    """
    Indicates that the address requested is already in use by the class that threw the Exception
    This is a non-fatal event and can be safely handled at runtime, occasionally with a retry
    """
    pass


class InvalidAddress(AddressError):
    """
    Indicates that the address requested is not a valid IP address
    This is non-fatal in general, but also should not be retried with the same address
    """
    pass


@total_ordering
class Location(ITObject):
    """
    Location of a service on a network, designated by a host name and a port number.

    :param host: Hostname representation.
    :param port: Port representation.
    """

    def __init__(self, host: HostnameRepr = None, port: PortRepr = None) -> None:
        super().__init__()
        self._hostname = as_hostname(host)
        self._port = as_port(port)

    @property
    def hostname(self) -> Hostname:
        """
        Returns the hostname of this location.
        """
        return self._hostname

    @property
    def port(self) -> Port:
        """
        Returns the port of this location.
        """
        return self._port

    def hostname_as_address(self) -> Address:
        """
        Provided the hostname corresponds to a duly formed IP address, this returns the address object corresponding to
        the location's hostname.
        """
        if not isinstance(self.hostname, _BaseAddress):
            raise ValueError("Location carries a domain name for host, which resolution must be simulated explicitly.")
        return cast(Address, self._hostname)

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, Location):
            raise ValueError(f"Cannot compare for equality {str(self)} to {str(other)} (type {type(other)}).")
        return self.hostname == other.hostname and self.port == other.port

    def __str__(self) -> str:
        return f"{str(self.hostname)}:{str(self.port)}"

    def __repr__(self) -> str:
        return repr(str(self))

    def __hash__(self) -> int:
        return hash(str(self))

    def __lt__(self, other) -> bool:
        if not isinstance(other, Location):
            raise ValueError(f"Cannot compare for order {str(self)} to {str(other)} (type {type(other)}).")
        if self.hostname == other.hostname:
            return self.port < other.port
        return str(self.hostname) < str(other.hostname)


@unique
class PayloadDictionaryType(Enum):
    CONTENT = 0
    CONTENT_TYPE = 1
    HOSTNAME = 2
    ADDRESS = 3


class Payload(ITObject):

    def __init__(self, entries: Dict[PayloadDictionaryType, object] = {}) -> None:
        super().__init__()
        self._entries = entries

    @property
    def entries(self) -> Dict[PayloadDictionaryType, object]:
        return self._entries

    # Mainly for testing
    def __eq__(self, other) -> bool:
        if other is None:
            return False

        if not isinstance(other, Payload):
            return False

        return self._entries == other._entries

    def __str__(self):
        return "<%s>" % ", ".join(["%s: %s" % (k, v) for k, v in self.entries.items()])


class Packet(_Packet):
    """
    Embodiment of a packet of data relayed over a link managed as a IP network.

    :param source: Source location of the packet.
    :param dest: Destination location where the packet is being relayed.
    :byte_size: Size of the packet's payload, in bytes.
    :payload: Optional free-form data used as a helper for implementing certain models. Not used by ITsim.
    """

    def __init__(self,
                 source: Location,
                 dest: Location,
                 byte_size: int,
                 payload: Payload = Payload()) -> None:
        super().__init__()
        self._source = source
        self._dest = dest
        self._byte_size = byte_size
        self._payload = payload

    @property
    def source(self) -> Location:
        """
        Location object representing the place this Packet was sent from
        """
        return self._source

    @property
    def dest(self) -> Location:
        """
        Location object representing the place this Packet was sent to
        """
        return self._dest

    @property
    def byte_size(self) -> int:
        """
        Size of the packet in bytes
        """
        return self._byte_size

    @property
    def payload(self) -> Payload:
        """
        Payload of the packet represented as a Dictionary of Enum members and arbitrary values

        Defaults to a payload with an empty dictionary
        """
        return self._payload

    def __len__(self) -> int:
        """
        Convenience method to give the Packet a notion of size
        """
        return self._byte_size

    # Mainly for testing
    def __eq__(self, other) -> bool:

        if other is None:
            return False

        if not isinstance(other, Packet):
            return False

        return self.source == other.source \
            and self.dest == other.dest \
            and self.byte_size == other.byte_size \
            and self.payload == other.payload

    def __str__(self):
        return "<Src: %s, Dest: %s, Size: %s, Payload: %s>" % (self.source, self.dest, self.byte_size, self.payload)


class Connection(object):
    """
    Connection object, tying a network interface of a node to a certain link.
    """

    def setup(self, *services: Service):
        """
        Lists services that the node connected to the link should arrange and get running.
        """
        raise NotImplementedError()


class Link(ITObject):
    """
    Physical medium network communications, intended to support a certain IP network.

    :param c: CIDR prefix for the network supported by the link instance.
    :param latency:
        Latency model (PRNG) for packets exchanged on this link (sampled every time a packet is transmitted on
        this link).
    :param bandwidth:
        Bandwidth (PRNG) for packets exchanged on this link (idem).
    """

    def __init__(self, c: CidrRepr, latency: VarRandomTime, bandwidth: VarRandomBandwidth) -> None:
        super().__init__()
        self._cidr = as_cidr(c)
        self._latency = latency
        self._bandwidth = bandwidth

    @property
    def cidr(self) -> Cidr:
        """Returns the CIDR descriptor of the network."""
        return self._cidr
        return

    def connected_as(self, ar: AddressRepr = None) -> Connection:
        """
        Generates a Connection instance to tie a certain node to this network. This connection object requests
        from an incipient node that, in order to be connected to this link, it implements a certain number of network
        services.

        :param ar: Address the node should take on this link.  If an integer is given, it is considered as the host
            number of the machine on this network. In other words, this number is added to the link's network number to
            form the node's full address.  The use of None as address gives the node address 0.0.0.0 (which is fine if
            it uses DHCP to receive an address from a router node).
        """
        if ar is None:
            ar = "0.0.0.0"
        raise NotImplementedError()

    def iter_nodes(self) -> Iterator[_Node]:
        """
        Iteration over the nodes connected to a link.
        """
        raise NotImplementedError()


# === WARNING -- The following code is deprecated and will be replaced presently. ===


class NetworkFull(Exception):
    pass


class CannotForward(AddressError):
    pass


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
