from typing import Set

import pytest

from greensim.random import constant
from itsim.software.context import Context
from itsim.machine.endpoint import Endpoint
from itsim.network.link import Link
from itsim.simulator import Simulator
from itsim.types import Address, as_cidr, as_address, Protocol
from itsim.units import S, MS, KB


Log = Set[str]

CIDR = as_cidr("10.10.0.0/16")
NUM_ENDPOINTS = 50

TIME_BIT_FIRST = 10 * MS
TIME_BIT_LAST = 10 * MS
LEN_PACKET = 1 * KB
LATENCY = TIME_BIT_FIRST
BANDWIDTH = LEN_PACKET / TIME_BIT_LAST
TIME_TRANSFER = LATENCY + LEN_PACKET / BANDWIDTH

PORT_SERVICE = 10987


def get_my_address(context: Context) -> Address:
    for addr in context.node.addresses():
        if addr in CIDR:
            return addr
    else:
        pytest.fail("This node has no address.")


def client(context: Context) -> None:
    num = int(get_my_address(context)) - int(CIDR.network_address)
    with context.node.bind(Protocol.UDP) as socket:
        assert socket.port != PORT_SERVICE
        socket.send((as_address(NUM_ENDPOINTS - num - 1, CIDR), PORT_SERVICE), LEN_PACKET)


def server(context: Context, log: Log) -> None:
    for address in context.node.addresses():
        if address in CIDR:
            break
    else:
        pytest.fail("No address in CIDR?")

    with context.node.bind(Protocol.UDP, PORT_SERVICE) as socket:
        packet = socket.recv()
        assert address == packet.dest.hostname_as_address()
        log.add((packet.source.hostname_as_address(), packet.dest.hostname_as_address()))


def test_context_networking():
    assert NUM_ENDPOINTS > 0
    log: Log = set()

    sim = Simulator()
    link = Link(CIDR, constant(LATENCY), constant(BANDWIDTH))
    for n in range(NUM_ENDPOINTS):
        Endpoint().connected_to(link, n) \
            .with_proc(sim, server, log) \
            .with_proc_in(sim, 1 * S, client)
    sim.run()

    assert log == {(as_address(n, CIDR), as_address(NUM_ENDPOINTS - n - 1, CIDR)) for n in range(NUM_ENDPOINTS)}
