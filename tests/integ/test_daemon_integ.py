from itsim import _Packet
from itsim.machine.node import Socket
from itsim.machine.process_management import _Thread
from itsim.machine.process_management.daemon import Daemon
from itsim.network.internet import Host
from itsim.network.location import Location
from itsim.network.packet import Packet
from itsim.simulator import Simulator
from itsim.types import as_port, Protocol

host = Host()
sim = Simulator()
packet_count = {}
n = 3
port_list = [80, 123, 321, 433]


@host.networking_daemon(sim, Protocol.TCP, 80, 433)
def net_a(thread: _Thread, packet: _Packet, socket: Socket) -> None:
    global packet_count

    if packet.dest.port in packet_count:
        packet_count[packet.dest.port] += 1
    else:
        packet_count[packet.dest.port] = 1

    # Exactly one additional Thread should be available for more incoming packets
    assert len(thread._process._threads) == 2


@host.networking_daemon(sim, Protocol.UDP, 123, 321)
class Net_B(Daemon):
    def __init__(self):
        self._trigger_event = net_a


def pack_send():
    for _ in range(n):
        for port in port_list:
            bound_sock = host._sockets[as_port(port)]
            bound_sock._enqueue(Packet(Location(), Location(None, bound_sock.port), 0))


sim.add_in(1, pack_send)

sim.run()

for p in port_list:
    assert packet_count[p] == n