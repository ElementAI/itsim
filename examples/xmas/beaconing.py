import pytest

from greensim.random import uniform, constant

from itsim import malware
from itsim.software.context import Context
from itsim.machine.endpoint import Endpoint
from itsim.machine.socket import Timeout
from itsim.network.location import Location
from itsim.network.link import Link
from itsim.network.router import Router
from itsim.simulator import Simulator, now
from itsim.types import Protocol
from itsim.units import S, MS, MbPS

ledger = set()


@malware
def client(context: Context, router: Router) -> None:
    with context.node.bind(Protocol.UDP) as socket:
        socket.send(router.location, 4, {"content": "ping",
                                         Router.FINAL_DEST_FIELD: Location("10.11.12.20", 9887),
                                         Router.MAC_FIELD: context.node.uuid})
        try:
            packet = socket.recv(1 * S)
        except Timeout:
            pytest.fail("Supposed to receive the packet before timeout.")
        assert packet.byte_size == 8
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
        assert packet.byte_size == 4
        assert packet.payload["content"] == "ping"
        socket.send(packet.source, 8, {"content": "pong", Router.MAC_FIELD: packet.payload[Router.MAC_FIELD]})
        ledger.add("server")


def test_packet_transfer():
    sim = Simulator()

    link = Link("10.11.12.0/24", latency=uniform(100 * MS, 200 * MS), bandwidth=constant(100 * MbPS))
    router = Router(sim, link)

    pinger = Endpoint().connected_to_static(link, "10.11.12.10")
    pinger.run_proc_in(sim, 0.1, client, router)

    ponger = Endpoint().connected_to_static(link, "10.11.12.20")
    ponger.run_proc(sim, server)

    sim.run(10.0 * S)

    assert ledger == {"client", "server"}
