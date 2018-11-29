from greensim.random import uniform, constant

from itsim.machine.endpoint import Endpoint
from itsim.network.link import Link
from itsim.network.router import Router
from itsim.network.service.dhcp import DHCPDaemon, dhcp_client
from itsim.simulator import Simulator
from itsim.types import Protocol, AddressRepr, as_address
from itsim.units import S, MS, MbPS


def set_addresses(*ars: AddressRepr):
    return {as_address(ar) for ar in ars}


def test_dhcp_exchange():
    sim = Simulator()

    link = Link("10.1.128.0/18", uniform(100 * MS, 200 * MS), constant(100 * MbPS))
    router = Router().connected_to(link, "10.1.128.1")
    router.networking_daemon(sim, Protocol.UDP, 67)(DHCPDaemon(100, link.cidr, as_address("10.1.128.1")))

    endpoints = [Endpoint().connected_to(link) for n in range(3)]
    for endpoint in endpoints:
        endpoint.fork_exec_in(sim, 0.0, dhcp_client, endpoint._interfaces[link.cidr])
        assert set(endpoint.addresses()) == set_addresses("127.0.0.1", link.cidr.network_address)

    sim.run(10.0 * S)

    all_addresses = set()
    for endpoint in endpoints:
        addresses = set(endpoint.addresses())
        assert len(addresses) == 2
        assert link.cidr.network_address not in addresses
        all_addresses.update(addresses)

    assert all_addresses == set_addresses("127.0.0.1", *[as_address(n + 100, link.cidr) for n in range(len(endpoints))])
