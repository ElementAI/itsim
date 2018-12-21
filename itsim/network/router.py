from itsim.machine.node import Node
from itsim.network.packet import Packet


class Router(Node):
    """
    Node tasked with forwarding messages between LANs connected to it, and over to a WAN interface. The router is
    configured through links it forwards between, and thus is made to implement certain network services over the
    appropriate links.

    :param wan: WAN interface, articulated by a ``itsim.network.Link`` instance.
    :param lan: LAN links connected to this router.
    """

    def __init__(self) -> None:
        super().__init__()

    def handle_packet_transit(self, packet: Packet) -> None:
        interface, address_hop = self._solve_transfer(packet.dest.hostname_as_address())
        interface.link._transfer_packet(packet, address_hop)
