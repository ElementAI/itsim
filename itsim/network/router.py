from itsim.machine.node import Node
from itsim.machine.process_management.daemon import Daemon
from itsim.machine.socket import Socket
from itsim.network.link import Link
from itsim.network.location import Location
from itsim.network.packet import Packet
from itsim.network.route import Local
from itsim.simulator import Simulator
from itsim.software.context import Context

from typing import cast, MutableMapping


class _PassThroughRoutingDaemon(Daemon):
    def __init__(self):
        super().__init__(self._route)
        self._mac_map: MutableMapping[str, Location] = {}

    def _route(self, context: Context, packet: Packet, socket: Socket):
        if Router.MAC_FIELD not in packet.payload:
            return

        mac = str(packet.payload[Router.MAC_FIELD])
        if Router.FINAL_DEST_FIELD in packet.payload and isinstance(packet.payload[Router.FINAL_DEST_FIELD], Location):
            if mac not in self._mac_map:
                self._mac_map[mac] = packet.source

            dest = cast(Location, packet.payload[Router.FINAL_DEST_FIELD])
        else:
            if mac not in self._mac_map:
                return
            dest = self._mac_map[mac]

        socket.send(dest, packet.byte_size, packet.payload)


class Router(Node):
    """
    Node tasked with forwarding messages between LANs connected to it, and over to a WAN interface. The router is
    configured through links it forwards between, and thus is made to implement certain network services over the
    appropriate links.

    :param wan: WAN interface, articulated by a ``itsim.network.Link`` instance.
    :param lan: LAN links connected to this router.
    """

    FINAL_DEST_FIELD = "final_dest"
    MAC_FIELD = "mac"

    def __init__(self, sim: Simulator, link: Link) -> None:
        super().__init__()
        self.addr = next(link.cidr.hosts())
        self._port = 53
        self._connect_to(link, self.addr, [Local("0.0.0.0/0")])

    def handle_packet_transit(self, packet: Packet) -> None:
        interface, address_hop = self._solve_transfer(packet.dest.hostname_as_address())
        interface.link._transfer_packet(packet, address_hop)
