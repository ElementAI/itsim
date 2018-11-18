from typing import Iterator, Set

from greensim.random import constant

from itsim.machine import _Node
from itsim.network import _Connection, _Link
from itsim.random import VarRandomTime, VarRandomBandwidth
from itsim.types import CidrRepr, Cidr, as_cidr, AddressRepr
from itsim.units import GbPS


class Link(_Link):
    """
    Physical medium network communications, intended to support a certain IP network.

    :param c: CIDR prefix for the network supported by the link instance.
    :param latency:
        Latency model (PRNG) for packets exchanged on this link (sampled every time a packet is transmitted on
        this link).
    :param bandwidth:
        Bandwidth (PRNG) for packets exchanged on this link (idem).
    """

    def __init__(self, c: CidrRepr, latency: VarRandomTime, bandwidth: VarRandomBandwidth) -> None:
        super().__init__()
        self._cidr = as_cidr(c)
        self._latency = latency
        self._bandwidth = bandwidth
        self._nodes: Set[_Node] = set()

    @property
    def cidr(self) -> Cidr:
        """Returns the CIDR descriptor of the network."""
        return self._cidr

    def connected_as(self, ar: AddressRepr = None) -> _Connection:
        """
        Generates a Connection instance to tie a certain node to this network. This connection object requests
        from an incipient node that, in order to be connected to this link, it implements a certain number of network
        services.

        :param ar: Address the node should take on this link.  If an integer is given, it is considered as the host
            number of the machine on this network. In other words, this number is added to the link's network number to
            form the node's full address.
        """
        raise NotImplementedError()

    def iter_nodes(self) -> Iterator[_Node]:
        """
        Iteration over the nodes connected to a link.
        """
        raise NotImplementedError()

    def _connect(self, node: _Node) -> None:
        self._nodes.add(node)


class Loopback(Link):

    def __init__(self):
        super().__init__("127.0.0.0/8", constant(0), constant(100 * GbPS))
