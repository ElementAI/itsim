from abc import ABC, abstractmethod
from enum import Enum, IntFlag, unique
from ipaddress import ip_address, \
    IPv4Address, IPv6Address, IPv4Network, IPv6Network, ip_network, _BaseNetwork
from typing import Optional, Union, Iterable, Tuple


Address = Union[IPv4Address, IPv6Address]
AddressRepr = Union[None, str, int, Address]
PortRepr = Optional[int]
Port = int
HostnameRepr = AddressRepr
Hostname = Union[Address, str]
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


def as_hostname(hr: HostnameRepr) -> Hostname:
    try:
        return as_address(hr)
    except ValueError:
        if isinstance(hr, str) and len(hr) > 0:
            return hr
        else:
            raise


class Protocol(IntFlag):
    # Transport
    UDP = 0x1
    TCP = 0x2
    BOTH = UDP | TCP
    # Confidentiality protection
    CLEAR = 0x40000000
    SSL = 0x80000000
    ANY = CLEAR | SSL


class Ports(ABC):
    """
    Collection of ports that may be set as part of a rule.
    """

    @staticmethod
    def all():
        return PortRange(0, 65536)

    @abstractmethod
    def __contains__(self, port: Port) -> bool:
        raise NotImplementedError()


class PortSet(Ports):
    """
    Port collection based on an exhaustive set.
    """

    def __init__(self, ports: Iterable[Port]) -> None:
        """
        - :param ports: Ports assembled into the set.
        """
        raise NotImplementedError()

    def __contains__(self, port: Port) -> bool:
        raise NotImplementedError()


class PortRange(Ports):
    """
    Port collection based on a functional interval.
    """

    def __init__(self, lower: Port, upper: Port) -> None:
        """
        The functional interval is [lower, upper[.
        """
        raise NotImplementedError()

    def __contains__(self, port: Port) -> bool:
        raise NotImplementedError()


PortsRepr = Union[Port, Iterable[Port], Tuple[Port, Port], Ports]


class SystemCall(ABC):
    """
    Under construction. Since OS functions are being captured in Node, I think it is likely that these will need
    to be implemented specifically.

    Not used in this demo.
    """
    @abstractmethod
    def make_call(self):
        pass


@unique
class Interrupt(Enum):
    """
    Under construction. This borrows from the UNIX convention of numbering the signals.

    Not used in this demo.
    """
    SIGINT = 0
    SIGKILL = 1
