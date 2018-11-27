from contextlib import ExitStack
from unittest.mock import patch

import pytest

from greensim.random import constant

from itsim.machine.endpoint import Endpoint
from itsim.network.link import Link, NoSuchAddress
from itsim.network.location import Location
from itsim.network.packet import Packet
from itsim.simulator import Simulator
from itsim.types import as_address
from itsim.units import S, B


DURATION_TRANSFER_BIT_FIRST = 1 * S
LATENCY = DURATION_TRANSFER_BIT_FIRST
DURATION_TRANSFER_BIT_LAST = 1 * S
SIZE_PACKET = 1000 * B
BANDWIDTH = 8 * SIZE_PACKET / DURATION_TRANSFER_BIT_LAST  # Expressed in bits / second.
DURATION_TRANSFER_TOTAL = DURATION_TRANSFER_BIT_FIRST + DURATION_TRANSFER_BIT_LAST


@pytest.fixture
def link():
    return Link("192.168.1.0/24", latency=constant(LATENCY), bandwidth=constant(BANDWIDTH))


@pytest.fixture
def laurel(link):
    return Endpoint().connected_to(link, "192.168.1.4")


@pytest.fixture
def hardy(link):
    return Endpoint().connected_to(link, "192.168.1.78")


@pytest.fixture
def packet(hardy):
    return Packet(Location("192.168.1.6", 9887), Location(next(hardy.addresses()), 25001), SIZE_PACKET)


def run_simulation(link, packet, address_dest):
    def transmit():
        link._transfer_packet(packet, address_dest)

    sim = Simulator()
    sim.add(transmit)
    sim.run()

    return sim.now()


def test_link_transfer_packet(link, laurel, hardy, packet):
    for endpoint in [laurel, hardy]:
        with patch.object(endpoint, "_receive_packet") as mock:
            address = next(address for address in endpoint.addresses() if address in link.cidr)
            assert run_simulation(link, packet, address) == pytest.approx(DURATION_TRANSFER_TOTAL)
            mock.assert_called_with(packet)


def test_link_transfer_packet_bad_address(link, packet):
    with pytest.raises(NoSuchAddress):
        run_simulation(link, packet, as_address("192.168.1.99"))


@patch("itsim.simulator.add_in")
def test_link_transfer_broadcast_no_one(mock, link):
    link._transfer_packet(
        Packet(Location("192.168.1.34", 56788), Location("192.168.1.255", 10987), 1234),
        as_address("192.168.1.255")
    )
    mock.assert_not_called()


def test_link_transfer_broadcast(link, laurel, hardy):
    with ExitStack() as exit_stack:
        mocks = [exit_stack.enter_context(patch.object(node, "_receive_packet")) for node in [laurel, hardy]]

        sim = Simulator()
        packet = Packet(Location("192.168.1.34", 56788), Location("192.168.1.255", 9887), SIZE_PACKET)

        def do_transfer():
            link._transfer_packet(packet, as_address("192.168.1.255"))

        sim.add(do_transfer)
        sim.run()

        for mock in mocks:
            mock.assert_called_with(packet)
