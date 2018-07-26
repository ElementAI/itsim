from ipaddress import IPv4Address, IPv6Address, ip_address
from typing import Union


Address = Union[IPv4Address, IPv6Address]
Addressable = Union[None, str, int, Address]
Port = int


def as_address(aa: Addressable) -> Address:
    if aa is None:
        return ip_address(0)
    elif isinstance(aa, int) or isinstance(aa, str):
        return ip_address(aa)
    return aa
