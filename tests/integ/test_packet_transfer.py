import pytest

from greensim.random import uniform, constant

from itsim.machine.endpoint import Endpoint
from itsim.machine.process_management.thread import Thread
from itsim.machine.socket import Timeout
from itsim.network.link import Link
from itsim.simulator import Simulator
from itsim.units import S, MS, MbPS


def client(thread: Thread) -> None:
    with thread.process.node.bind() as socket:
        socket.send(("10.11.12.20", 9887), 4, {"content": "ping"})
        packet = socket.recv(1 * S)
        assert packet.num_bytes == 8
        assert packet.payload["content"] == "pong"

    try:
        socket.recv(5 * S)
        pytest.fail()
    except Timeout:
        pass


def server(thread: Thread) -> None:
    with thread.process.node.bind(9887) as socket:
        while True:
            packet = socket.recv()
            assert packet.num_bytes == 4
            assert packet.payload["content"] == "ping"
            socket.send(packet.src, 8, {"content": "pong"})


def test_packet_transfer():
    sim = Simulator()

    link = Link("10.11.12.0/24", latency=uniform(100 * MS, 200 * MS), bandwidth=constant(100 * MbPS))
    pinger = Endpoint().connected_to(link, "10.11.12.10")
    pinger.fork_exec_in(sim, 0.1, client)
    ponger = Endpoint().connected_to(link, "10.11.12.20")
    ponger.fork_exec(sim, server)

    sim.run(10.0 * S)
