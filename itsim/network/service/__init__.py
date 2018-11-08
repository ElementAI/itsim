from typing import Tuple, Mapping

from itsim.machine.process_management.daemon import Service
from itsim.types import AddressRepr, Port


class DHCP(Service):
    """
    Network service that operates DHCP address delivery service on a given interface.
    """

    def __init__(self):
        raise NotImplementedError()


class NAT(Service):
    """
    Network service that operates network address translation when speaking across a given interface.
    """

    def __init__(self):
        raise NotImplementedError()


RulesForward = Mapping[Port, Tuple[AddressRepr, Port]]


class PortForwarding(Service):
    """
    Network service that forwards ports from a given interface to a certain machines, at an equivalent range of ports.

    :param rules_fw: Rules explaining where to forward certain input ports on the associated interface.
    """

    def __init__(self, rules_forward: RulesForward) -> None:
        raise NotImplementedError()
