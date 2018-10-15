from typing import Tuple, Iterable

from itsim.types import AddressRepr


class DHCP(object):
    """
    Network service that operates DHCP address delivery service on a given interface.
    """

    def __init__(self):
        raise NotImplementedError()


class NAT(object):
    """
    Network service that operates network address translation when speaking across a given interface.
    """

    def __init__(self):
        raise NotImplementedError()


RulesFw = Mapping[Port, Tuple[AddressRepr, Port]]


class PortForwarding(object):
    """
    Network service that forwards ports from a given interface to a certain machines, at an equivalent range of ports.
    """

    def __init__(self, rules_fw: RulesFw):
        """
        - :param rules_fw: Rules explaining where to forward certain input ports on the associated interface.
        """
        raise NotImplementedError()
