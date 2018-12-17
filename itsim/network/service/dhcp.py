from greensim.random import normal

from itsim.network import _Packet
from itsim.software.context import Context
from itsim.machine.socket import Socket
from itsim.machine.process_management.daemon import Daemon
from itsim.random import num_bytes
from itsim.units import B


class DHCPDaemon(Daemon):
    responses = {"DHCPDISCOVER": "DHCPOFFER", "DHCPREQUEST": "DHCPACK"}
    size_packet_dhcp = num_bytes(normal(100.0 * B, 30.0 * B), header=240 * B)

    def __init__(self) -> None:
        pass

    def _trigger_event(self, context: Context, packet: _Packet, socket: Socket) -> None:
        type_msg = packet.payload["content"]
        if type_msg in self.responses:
            socket.send(packet.source,
                        next(self.size_packet_dhcp),
                        {"content": self.responses[type_msg]})
