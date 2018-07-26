from ipaddress import IPv4Address, IPv6Address, ip_address
from typing import Union, Optional


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
