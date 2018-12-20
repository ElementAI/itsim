from itsim.machine.node import Node
from itsim.network.link import Link
from itsim.network.packet import Packet
from itsim.network.route import Local
from itsim.simulator import Simulator


class Router(Node):
    """
    Node tasked with forwarding messages between LANs connected to it, and over to a WAN interface. The router is
    configured through links it forwards between, and thus is made to implement certain network services over the
    appropriate links.

    :param wan: WAN interface, articulated by a ``itsim.network.Link`` instance.
    :param lan: LAN links connected to this router.
    """

    def __init__(self, sim: Simulator, link: Link) -> None:
        super().__init__()
        self.addr = next(link.cidr.hosts())
        self._port = 53
        self._connect_to(link, self.addr, [Local("0.0.0.0/0")])

    def handle_packet_transit(self, packet: Packet) -> None:
        interface, address_hop = self._solve_transfer(packet.dest.hostname_as_address())
        interface.link._transfer_packet(packet, address_hop)
