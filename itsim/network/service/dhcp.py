from greensim.random import normal

from itsim import _Packet
from itsim.machine.node import Socket
from itsim.machine.process_management import _Thread
from itsim.machine.process_management.daemon import Daemon
from itsim.network.packet import Payload, PayloadDictionaryType
from itsim.random import num_bytes
from itsim.units import B


class DHCPDaemon(Daemon):
    responses = {"DHCPDISCOVER": "DHCPOFFER", "DHCPREQUEST": "DHCPACK"}
    size_packet_dhcp = num_bytes(normal(100.0 * B, 30.0 * B), header=240 * B)

    def _trigger_event(self, thread: _Thread, packet: _Packet, socket: Socket):
        type_msg = packet.payload.entries[PayloadDictionaryType.CONTENT]
        if type_msg in self.responses:
            socket.send(packet.source,
                        next(self.size_packet_dhcp),
                        Payload({PayloadDictionaryType.CONTENT: self.responses[type_msg]}))
