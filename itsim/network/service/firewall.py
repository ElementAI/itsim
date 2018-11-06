from abc import abstractmethod
from typing import Iterable, Optional

from itsim import ITObject
from itsim.node.process_management.daemon import Service
from itsim.types import CidrRepr, Ports, PortsRepr, Protocol


class Rule(ITObject):
    """
    Firewall rule: determines whether a certain category of packets is allowed through a firewall or not.

    :param origin: CIDR prefix indicating the provenance of packets that can match this rule.
    :param protocol: Transport protocol carrying packets that can match this rule.
    :param ports: List of ports tagged on packets that can match this rule.
    """

    def __init__(self, origin: CidrRepr, protocol: Protocol, ports: PortsRepr) -> None:
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

    @staticmethod
    def all():
        return Allow("0.0.0.0/0", Protocol.BOTH, Ports.all())

    def is_allowed(self) -> bool:
        return True


class Deny(Rule):
    """
    Firewall rule that denies packet traversal.
    """

    @staticmethod
    def all():
        return Deny("0.0.0.0/0", Protocol.BOTH, Ports.all())

    def is_allowed(self) -> bool:
        return False


class Firewall(Service):
    """
    Network service that controls which packets it lets through its associated interface, either to the node (inbound)
    or from the node (outbound).

    :param inbound:
        List of firewall rules as to which packets should be accepted through the interface and relayed to the node.
        By default, the firewall blocks everything inbound (that's not part of an already established connection).
        This list of rules is prepended on top of this default catch-all.
    :param outbound:
        List of firewall rules as to which packets emitted by the node should be allowed through and put on the
        link. By default, the firewall allows everything outbound. This list of rules is prepended on top of this
        default catch-all.
    """

    def __init__(self, inbound: Optional[Iterable[Rule]] = None, outbound: Optional[Iterable[Rule]] = None) -> None:
        raise NotImplementedError()
