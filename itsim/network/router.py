from itsim.machine.node import Node
from itsim.machine.process_management.daemon import Daemon
from itsim.machine.socket import Socket
from itsim.network.link import Link
from itsim.network.location import Location
from itsim.network.packet import Packet
from itsim.network.route import Relay
from itsim.simulator import Simulator
from itsim.software.context import Context
from itsim.types import Protocol

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
        addr = next(link.cidr.hosts())
        port = 53
        self._connect_to(link, addr, [Relay(addr, link.cidr)])
        self.run_networking_daemon(sim, _PassThroughRoutingDaemon(), Protocol.UDP, port)
        self.location = Location(addr, port)
