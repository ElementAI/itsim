from itsim.machine.process_management.__init__ import _Thread
from itsim.machine.process_management.daemon import Daemon
from itsim.network.internet import Host
from itsim.network.location import Location
from itsim.network.packet import Packet, Payload
from itsim.simulator import Simulator
from itsim.types import as_port, Protocol

host = Host()
sim = Simulator()


@host.networking_daemon(sim, Protocol.TCP, 80, 433)
def net_a(thread: _Thread, packet: Packet) -> None:
    print("Got a packet at port %s!" % packet.dest.port)


@host.networking_daemon(sim, Protocol.UDP, 123, 321)
class Net_B(Daemon):
    def __init__(self):
        self._trigger_event = net_a


def pack_send():
    for _ in range(3):
        for port in [80, 433, 123, 321]:
            bound_sock = host._port_table[as_port(port)]
            bound_sock._enqueue(Packet(Location(), bound_sock._src, 0, Payload()))


sim.add_in(1, pack_send)

sim.run()
