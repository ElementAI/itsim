from ipaddress import ip_address, \
    IPv4Address, IPv6Address, IPv4Network, IPv6Network, ip_network, _BaseNetwork
from typing import Optional, Union


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
