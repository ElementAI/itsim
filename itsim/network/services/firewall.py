from abc import ABC, abstractmethod
from enum import Flag, auto
from typing import Iterable, Tuple, Union

from itsim.types import CidrRepr, Port


class Protocol(Flag):
    UDP = auto
    TCP = auto
    BOTH = UDP | TCP


class Ports(ABC):
    """
    Collection of ports that may be set as part of a rule.
    """
    ALL = PortInterval(0, 65536)

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


PortsRepr = Union[Iterable[Port], Tuple[Port, Port]]


class Rule(ABC):
    """
    Firewall rule: determines whether a certain category of packets is allowed through a firewall or not.
    """

    def __init__(origin: CidrRepr, protocol: Protocol, ports: PortsRepr) -> None:
        """
        - :param origin: CIDR prefix indicating the provenance of packets that can match this rule.
        - :param protocol: Transport protocol carrying packets that can match this rule.
        - :param ports: List of ports tagged on packets that can match this rule.
        """
        raise NotImplementedError()

    @abstractmethod
    def is_allowed(self) -> bool:
        """
        Determines whether a packet matching this rule will be allowed through the firewall.
        """
        return True


class Allow(Rule):
    """
    Firewall rule that allows packets through.
    """

    ALL = Allow("0.0.0.0/0", Protocol.BOTH, (0, 0xffff))

    def is_allowed(self) -> bool:
        return True


class Deny(Rule):
    """
    Firewall rule that denies packet traversal.
    """

    ALL = Deny("0.0.0.0/0", Protocol.BOTH, (0, 0xffff))

    def is_allowed(self) -> bool:
        return False


class Firewall(object):
    """
    Network service that controls which packets it lets through its associated interface, either to the node (inbound)
    or from the node (outbound).
    """

    def __init__(self, inbound: Iterable[Rule], outbound: Iterable[Rule]) -> None:
        """
        - :param inbound:
            List of firewall rules as to which packets should be accepted through the interface and relayed to the node.
            By default, the firewall blocks everything inbound (that's not part of an already established connection).
            This list of rules is prepended on top of this default catch-all.
        - :param outbound:
            List of firewall rules as to which packets emitted by the node should be allowed through and put on the
            link. By default, the firewall allows everything outbound. This list of rules is prepended on top of this
            default catch-all.
        """
        raise NotImplementedError()
