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
    """
    Returns a strict ``Address`` object from one of its representations:

        - ``None``, which designates address 0.0.0.0.
        - A string, in typical form (e.g. "a.b.c.d" for IPv4 addresses).
        - An integer, which is cast to an address in big-endian byte order.
        - An ``Address`` object, which is returned unaltered.
    """
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
    """
    Returns a strict network address expressed as in CIDR form: either a string, expressing the network address as
    ``"<network number><zeros>/<mask bits>"``, or as a ``Cidr`` object, which is returned unaltered.
    """
    if isinstance(cr, _BaseNetwork):
        return cr
    return ip_network(cr)


def as_port(pr: PortRepr) -> Port:
    """
    Return a port number from one of its representation: either the port number itself, or ``None``, which is
    assimilated to catch-all port number 0.
    """
    if pr is None:
        return 0
    if pr < 0 or pr >= 2 ** 16:
        raise ValueError(f"Given integer value {pr} does not correspond to a valid port.")
    return pr


def as_hostname(hr: HostnameRepr) -> Hostname:
    """
    Returns a hostname from one of its representations: either an address or a string bearing a name formatted according
    to RFC 1034 of the IETF.
    """
    try:
        return as_address(hr)
    except ValueError:
        if isinstance(hr, str) and len(hr) > 0:
            return hr
        else:
            raise


class Protocol(IntFlag):
    """
    Combinable indicators of network protocols, at the transport and application levels.
    """
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
    def all() -> "Ports":
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
        :param ports: Ports assembled into the set.
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
        The functional interval is ``[lower, upper[``.
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
