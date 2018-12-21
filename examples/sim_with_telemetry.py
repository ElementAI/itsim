from greensim.random import expo, constant

from itsim.datastore.datastore import DatastoreClientFactory
from itsim.machine.endpoint import Endpoint
from itsim.network.link import Link
from itsim.simulator import Simulator, advance
from itsim.software.context import Context
from itsim.types import as_cidr, Protocol
from itsim.units import MbPS, MS, S


PORT = 5678
CIDR = as_cidr("192.168.1.0/24")
NUM_CLIENTS = 5


def serve_pongs(context: Context) -> None:
    # import pdb; pdb.set_trace()
    with context.node.bind(Protocol.UDP, PORT) as socket:
        while True:
            packet = socket.recv()
            socket.send(packet.source, 4, {"what": "pong"})


def ask_ping(context: Context) -> None:
    # import pdb; pdb.set_trace()
    with context.node.bind(Protocol.UDP) as socket:
        socket.send((CIDR.network_address + 1, PORT), 4, {"what": "ping"})
        socket.recv()


def control(sim, pings):
    advance(10000)
    for proc_pinger in pings:
        proc_pinger.wait(NUM_CLIENTS * S)
    sim.stop()


def test_endpoint_telemetry():
    with Simulator() as sim:
        DatastoreClientFactory().sim_uuid = sim.uuid
        link = Link(CIDR, expo(10 * MS), constant(100 * MbPS))
        server = Endpoint().connected_to_static(link, 1)
        server.run_proc(sim, serve_pongs)

        endpoints = [Endpoint().connected_to_static(link, 100 + n) for n in range(NUM_CLIENTS)]
        pings = [endpoint.run_proc(sim, ask_ping) for endpoint in endpoints]

        sim.add(control, sim, pings)
        sim.run()
        return sim.uuid


uuid = test_endpoint_telemetry()
