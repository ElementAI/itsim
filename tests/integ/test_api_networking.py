from typing import Set, Mapping, Any

import pytest

from greensim.random import constant
from itsim.machine.api import API
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


def get_my_address(api: API) -> Address:
    for addr in api.addresses():
        if addr in CIDR:
            return addr
    else:
        raise RuntimeError("Why does this node have no address?")


def client(api: API) -> None:
    num = int(get_my_address(api)) - int(CIDR.network_address)
    with api.bind(Protocol.UDP) as socket:
        assert socket.port != PORT_SERVICE
        socket.send((as_address(NUM_ENDPOINTS - num - 1, CIDR), PORT_SERVICE), LEN_PACKET)


def server(api: API, log: Log) -> None:
    address = api.addresses()
    with api.bind(Protocol.UDP, PORT_SERVICE) as socket:
        packet = socket.recv()
        assert address == packet.dest.hostname_as_address()
        log.append((packet.src.hostname_as_address(), packet.dest.hostname_as_address()))


def test_api_networking() -> None:
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
