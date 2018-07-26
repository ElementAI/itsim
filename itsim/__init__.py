from functools import total_ordering
from ipaddress import IPv4Address, IPv6Address, ip_address
from typing import Union, Optional, Any


Address = Union[IPv4Address, IPv6Address]
AddressRepr = Union[None, str, int, Address]
PortRepr = Optional[int]
Port = int
HostRepr = AddressRepr
Host = Union[Address, str]


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
