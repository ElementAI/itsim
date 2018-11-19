from greensim.random import normal

from itsim.network import _Packet
from itsim.machine.node import Socket
from itsim.machine.process_management import _Thread
from itsim.machine.process_management.daemon import Daemon
from itsim.random import num_bytes
from itsim.units import B


class DHCPDaemon(Daemon):
    responses = {"DHCPDISCOVER": "DHCPOFFER", "DHCPREQUEST": "DHCPACK"}
    size_packet_dhcp = num_bytes(normal(100.0 * B, 30.0 * B), header=240 * B)

    def __init__(self, num_host_first: int = 1) -> None:
        super().__init__(self._on_packet)
        self._num_host_first = num_host_first

    def _on_packet(self, thread: _Thread, packet: _Packet, socket: Socket) -> None:
        type_msg = packet.payload["content"]
        if type_msg in self.responses:
            socket.send(packet.source,
                        next(self.size_packet_dhcp),
                        {"content": self.responses[type_msg]})
