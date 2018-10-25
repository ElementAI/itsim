from enum import Enum, unique
from functools import total_ordering
from ipaddress import _BaseAddress
from typing import Any, Dict, cast, Iterator

from itsim import _Node, _Packet, ITObject
from itsim.network.service import Service
from itsim.random import VarRandomTime, VarRandomBandwidth
from itsim.types import CidrRepr, Cidr, as_cidr, Address, AddressRepr, HostnameRepr, PortRepr, \
    as_hostname, as_port, Hostname, Port


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
