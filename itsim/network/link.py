from typing import Iterator, Set

from greensim.random import constant

from itsim.machine.__init__ import _Node
from itsim.network import _Connection, _Link
from itsim.network.packet import Packet
from itsim.random import VarRandomTime, VarRandomBandwidth
from itsim.simulator import add_in
from itsim.types import CidrRepr, Cidr, as_cidr, AddressRepr, Address
from itsim.units import GbPS


BANDWIDTH_MIN = 1.0 / 10.0  # 1 bit every 10 seconds


class NoSuchAddress(Exception):

    def __init__(self, address: Address) -> None:
        super().__init__()
        self.address = address


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
            form the node's full address.  The use of None as address gives the node address 0.0.0.0 (which is fine if
            it uses DHCP to receive an address from a router node).
        """
        raise NotImplementedError()

    def iter_nodes(self) -> Iterator[_Node]:
        """
        Iteration over the nodes connected to a link.
        """
        return iter(self._nodes)

    def _connect(self, node: _Node) -> None:
        self._nodes.add(node)

    def _transfer_packet(self, packet: Packet, hop: Address) -> None:
        # TODO -- Replace this inefficient loop with a sort of ARP
        for node, interface in [(node, interface) for node in self.iter_nodes() for interface in node.interfaces()]:
            if interface.address == hop:
                break
        else:
            raise NoSuchAddress(hop)

        packet_latency = next(self._latency)
        packet_bandwidth = next(self._bandwidth)  # Modeler's responsibility never to provide 0 bandwidth.
        duration = packet_latency + 8 * packet.byte_size / packet_bandwidth
        add_in(duration, node._receive_packet, packet)



class Loopback(Link):

    def __init__(self):
        super().__init__("127.0.0.0/8", constant(0), constant(100 * GbPS))
