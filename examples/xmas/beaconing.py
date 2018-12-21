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
from itsim.types import as_address, as_cidr, Protocol
from itsim.units import B, S, MS, MbPS

ledger = set()
size_dist = normal(100 * B, 300 * B)
ponger_addr = as_address("120.11.12.20")


@malware
def client(context: Context, router: Router) -> None:
    with context.node.bind(Protocol.UDP) as socket:
        while True:
            socket.send(Location(ponger_addr, 9887), next(size_dist), {"content": "ping"})
            try:
                packet = socket.recv(10 * S)
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
        while True:
            packet = socket.recv()
            assert packet.payload["content"] == "ping"
            socket.send(packet.source, 8, {"content": "pong"})
            ledger.add("server")


def test_packet_transfer():
    sim = Simulator()

    local_cidr = as_cidr("10.11.12.0/24")
    internet_cidr = as_cidr("0.0.0.0/0")
    local = Link(local_cidr, latency=uniform(100 * MS, 10 * MS), bandwidth=constant(100 * MbPS))
    internet = Link(internet_cidr, latency=uniform(1 * S, 1 * S), bandwidth=constant(1000 * MbPS))

    router = Router()
    router.connected_to_static(local, 1)
    router.connected_to_static(internet, "1.2.3.4")

    pinger_route = Relay(router._interfaces[local_cidr].address, internet_cidr)
    ponger_route = Relay(router._interfaces[internet_cidr].address, local_cidr)

    pinger = Endpoint().connected_to_static(local, "10.11.12.10", [pinger_route])
    pinger.run_proc_in(sim, 0.1, client, router)

    ponger = Endpoint().connected_to_static(internet, ponger_addr, [ponger_route])
    ponger.run_proc(sim, server)

    sim.run(600.0 * S)

    assert ledger == {"client", "server"}
