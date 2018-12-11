from typing import Set, Mapping, Any

import pytest

from greensim.random import constant
from itsim.machine.dashboard import Dashboard
from itsim.machine.endpoint import Endpoint
from itsim.network.link import Link
from itsim.simulator import Simulator, advance
from itsim.types import Address, as_cidr, as_address, Protocol
from itsim.units import S, MS, KB


Log = Set[str]

CIDR = as_cidr("10.10.0.0/16")
NUM_ENDPOINTS = 1000

TIME_BIT_FIRST = 10 * MS
TIME_BIT_LAST = 10 * MS
LEN_PACKET = 1 * KB
LATENCY = TIME_BIT_FIRST
BANDWIDTH = LEN_PACKET / TIME_BIT_LAST
TIME_TRANSFER = LATENCY + LEN_PACKET / BANDWIDTH

PORT_SERVICE = 10987


def get_my_address(d: Dashboard) -> Address:
    for addr in d.addresses():
        if addr in CIDR:
            return addr
    else:
        raise RuntimeError("Why does this node have no address?")


def client(d: Dashboard) -> None:
    num = int(get_my_address(d)) - int(CIDR.network_address)
    with d.bind(Protocol.UDP) as socket:
        assert socket.port != PORT_SERVICE
        socket.send((as_address(NUM_ENDPOINTS - num - 1, CIDR), PORT_SERVICE), LEN_PACKET)


def server(d: Dashboard, log: Log) -> None:
    address = d.addresses()
    with d.bind(Protocol.UDP, PORT_SERVICE) as socket:
        packet = socket.recv()
        assert address == packet.dest.hostname_as_address()
        log.append((packet.src.hostname_as_address(), packet.dest.hostname_as_address()))


def test_dashboard_networking() -> None:
    assert NUM_ENDPOINTS > 0
    log: Log = set()

    sim = Simulator()
    link = Link(CIDR, constant(LATENCY), constant(BANDWIDTH))
    endpoints = [
        Endpoint().connected_to(link, n).with_proc(sim, server, log).with_proc_in(sim, 1 * S, client)
        for n in range(NUM_ENDPOINTS)
    ]
    sim.run()

    assert log == {(as_address(n, CIDR), as_address(NUM_ENDPOINTS - n - 1, CIDR)) for n in range(NUM_ENDPOINTS)}
