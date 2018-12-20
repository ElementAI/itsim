import pytest

from greensim.random import constant, normal, uniform

from itsim import malware
from itsim.software.context import Context
from itsim.machine.endpoint import Endpoint
from itsim.machine.socket import Timeout
from itsim.network.location import Location
from itsim.network.link import Link
from itsim.network.router import Router
from itsim.network.route import Relay
from itsim.simulator import Simulator, now
from itsim.types import Protocol
from itsim.units import B, S, MS, MbPS

ledger = set()
size_dist = normal(100 * B, 300 * B)


@malware
def client(context: Context, router: Router) -> None:
    with context.node.bind(Protocol.UDP) as socket:
        socket.send(Location("10.11.12.20", 9887), next(size_dist), {"content": "ping"})
        try:
            packet = socket.recv(1 * S)
        except Timeout:
            pytest.fail("Supposed to receive the packet before timeout.")
        assert packet.payload["content"] == "pong"

        try:
            socket.recv(5 * S)
            pytest.fail()
        except Timeout:
            assert now() > 5.0
        finally:
            ledger.add("client")


@malware
def server(context: Context) -> None:
    with context.node.bind(Protocol.UDP, 9887) as socket:
        packet = socket.recv()
        assert packet.payload["content"] == "ping"
        socket.send(packet.source, 8, {"content": "pong"})
        ledger.add("server")


def test_packet_transfer():
    sim = Simulator()

    link = Link("10.11.12.0/24", latency=uniform(100 * MS, 10 * MS), bandwidth=constant(100 * MbPS))
    router = Router(sim, link)
    route = Relay(router.addr, "0.0.0.0/0")

    pinger = Endpoint().connected_to_static(link, "10.11.12.10", [route])
    pinger.run_proc_in(sim, 0.1, client, router)

    ponger = Endpoint().connected_to_static(link, "10.11.12.20", [route])
    ponger.run_proc(sim, server)

    sim.run(10.0 * S)

    assert ledger == {"client", "server"}
