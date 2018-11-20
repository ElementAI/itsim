from typing import List
# from unittest.mock import MagicMock, patch

from greensim.random import uniform, constant

from itsim.machine.endpoint import Endpoint
from itsim.machine.process_management import _Thread
from itsim.network.link import Link
from itsim.network.location import Location
from itsim.network.packet import Packet
from itsim.network.router import Router
from itsim.network.service.dhcp import DHCPDaemon
from itsim.simulator import Simulator, advance
from itsim.types import as_port, Protocol, AddressRepr, as_address
from itsim.units import MIN, S, MS, MbPS


def set_addresses(*ars: AddressRepr):
    return {as_address(ar) for ar in ars}


def test_dhcp_exchange():
    sim = Simulator()

    link = Link("10.1.128.0/18", uniform(100 * MS, 200 * MS), constant(100 * MbPS))
    router = Router().connected_to(link, "10.1.128.1") \
                     .with_daemon_on(sim, link, DHCPDaemon(100), Protocol.UDP, 67)

    endpoints = [Endpoint().connected_to(link, dhcp_with=sim) for n in range(3)]
    for endpoint in endpoints:
        assert set(endpoint.addresses()) == set_addresses("127.0.0.1", link.cidr.network_address)

    sim.run(10.0 * S)

    all_addresses = set()
    for endpoint in endpoints:
        addresses = set(endpoint.addresses())
        assert len(addresses) == 2
        assert link.cidr.network_address not in addresses
        all_addresses.update(addresses)

    assert all_addresses == set_addresses("127.0.0.1", *[as_address(n + 100, link.cidr) for n in range(len(endpoints))])
