from functools import total_ordering
from ipaddress import IPv4Address, IPv6Address, ip_address
from typing import Union, Optional, Any


Address = Union[IPv4Address, IPv6Address]
AddressRepr = Union[None, str, int, Address]
PortRepr = Optional[int]
Port = int


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


def as_port(ap: PortRepr) -> Port:
    if ap is None:
        return 0
    if ap < 0 or ap >= 2 ** 16:
        raise ValueError(f"Given integer value {ap} does not correspond to a valid port.")
    return ap


@total_ordering
class Location(object):

    def __init__(self, address: AddressRepr = None, port: PortRepr = None) -> None:
        super().__init__()
        self._address = as_address(address)
        self._port = as_port(port)

    @property
    def address(self) -> Address:
        return self._address

    @property
    def port(self) -> Port:
        return self._port

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, Location):
            return False
        return self.address == other.address and self.port == other.port

    def __str__(self) -> str:
        return f"({str(self.address)}, {str(self.port)})"

    def __repr__(self) -> str:
        return repr(str(self))

    def __lt__(self, other) -> bool:
        if not isinstance(other, Location):
            return False
        if self.address == other.address:
            return self.port < other.port
        return self.address < other.address
