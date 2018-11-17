from typing import Set

from greensim.random import uniform, constant

from itsim.machine.endpoint import Endpoint
from itsim.machine.process_management.thread import Thread
from itsim.network.link import Link
from itsim.simulator import Simulator, advance
from itsim.types import Address, as_address
from itsim.units import MS, S, MbPS


NUMS_HOST = list(range(100, 110))


class EndpointChattering(Endpoint):

    def __init__(self, sim):
        super().__init__()
        self._peers: Set[Address] = set()
        self._interval_broadcast = uniform(3.0 * S, 6.0 * S)
        self.fork_exec(sim, self.server)
        self.fork_exec(sim, self.client)

    def server(self, thread: Thread):
        with thread.process.node.bind(10000) as socket:
            while True:
                packet = socket.recv()
                self._peers.add(packet.source.hostname_as_address())

    def client(self, thread: Thread):
        with thread.process.node.bind() as socket:
            while True:
                advance(next(self._interval_broadcast))
                for interface in self.interfaces():
                    if not interface.address.is_loopback:
                        socket.send((interface.cidr.broadcast_address, 10000), 128)

    def assert_seen_all_peers(self, expected: Set[Address]):
        assert self._peers == expected


def test_broadcast():
    sim = Simulator()
    link = Link("10.11.0.0/16", uniform(100 * MS, 200 * MS), constant(100 * MbPS))
    endpoints = [EndpointChattering(sim).connected_to(link, as_address(n, link.cidr)) for n in NUMS_HOST]

    sim.run(10 * S)

    for endpoint in endpoints:
        endpoint.assert_seen_all_peers()
