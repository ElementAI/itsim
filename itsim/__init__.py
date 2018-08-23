from abc import ABC, abstractproperty
from functools import total_ordering
from ipaddress import \
    IPv4Address, IPv6Address, IPv4Network, IPv6Network, ip_address, ip_network, _BaseNetwork, _BaseAddress
from typing import cast, Union, Optional, Any, Iterable


# Time correspondance convention: 1.0 simulated time == 1.0 second
S = 1.0
MIN = 60 * S
H = 60 * MIN
D = 24 * H
W = 7 * D
MS = S * 1.0e-3
US = MS * 1.0e-6
NS = US * 1.0e-9

# Bandwidth units: B == bit, not byte
KbPS = 1024 / 8
MbPS = 1024 * KbPS
GbPS = 1024 * MbPS

# Size units: B == byte
B = 1
KB = 1024 * B
MB = 1024 * KB
GB = 1024 * MB


Address = Union[IPv4Address, IPv6Address]
AddressRepr = Union[None, str, int, Address]
PortRepr = Optional[int]
Port = int
HostRepr = AddressRepr
Host = Union[Address, str]
Cidr = Union[IPv4Network, IPv6Network]
CidrRepr = Union[str, Cidr]


def as_address(ar: AddressRepr) -> Address:
    if ar is None:
        return ip_address(0)
    elif isinstance(ar, int):
        if ar < 0 or ar >= 2 ** 32:
            raise ValueError(f"Given integer value {ar} does not correspond to a valid IPv4 address.")
        return ip_address(ar)
    elif isinstance(ar, str):
        return ip_address(ar)
    return ar


def as_cidr(cr: CidrRepr) -> Cidr:
    if isinstance(cr, _BaseNetwork):
        return cr
    return ip_network(cr)


def as_port(pr: PortRepr) -> Port:
    if pr is None:
        return 0
    if pr < 0 or pr >= 2 ** 16:
        raise ValueError(f"Given integer value {pr} does not correspond to a valid port.")
    return pr


def as_host(hr: HostRepr) -> Host:
    try:
        return as_address(hr)
    except ValueError:
        if isinstance(hr, str) and len(hr) > 0:
            return hr
        else:
            raise


@total_ordering
class Location(object):

    def __init__(self, host: HostRepr = None, port: PortRepr = None) -> None:
        super().__init__()
        self._host = as_host(host)
        self._port = as_port(port)

    @property
    def host(self) -> Host:
        return self._host

    @property
    def port(self) -> Port:
        return self._port

    def host_as_address(self) -> Address:
        if not isinstance(self.host, _BaseAddress):
            raise ValueError("Location carries a domain name for host, which resolution must be simulated explicitly.")
        return cast(Address, self._host)

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, Location):
            raise ValueError(f"Cannot compare for equality {str(self)} to {str(other)} (type {type(other)}).")
        return self.host == other.host and self.port == other.port

    def __str__(self) -> str:
        return f"{str(self.host)}:{str(self.port)}"

    def __repr__(self) -> str:
        return repr(str(self))

    def __hash__(self) -> int:
        return hash(str(self))

    def __lt__(self, other) -> bool:
        if not isinstance(other, Location):
            raise ValueError(f"Cannot compare for order {str(self)} to {str(other)} (type {type(other)}).")
        if self.host == other.host:
            return self.port < other.port
        return str(self.host) < str(other.host)


class Packet(object):  # Unimplemented yet

    def __init__(self) -> None:
        super().__init__()
        self.dest = Location()  # TBD


class _Node(ABC):

    @abstractproperty
    def addresses(self) -> Iterable[Address]:
        raise NotImplementedError("Meant to be implemented by class itsim.node.Node.")
        return []
