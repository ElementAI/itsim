import pytest

from greensim.random import constant

from itsim.network.forwarding import Local, Relay
from itsim.network.interface import Interface
from itsim.network.link import Link
from itsim.types import as_cidr, as_address
from itsim.units import MS, MbPS


CIDR_LOCAL = as_cidr("192.168.1.0/24")


@pytest.fixture
def link() -> Link:
    return Link("192.168.1.0/24", constant(1 * MS), constant(100 * MbPS))


@pytest.fixture
def interface_wo_address(link: Link) -> Interface:
    return Interface(link, as_address(None), [])


def test_address_default(interface_wo_address):
    assert interface_wo_address.address == as_address(None)


def test_set_address(interface_wo_address):
    interface_wo_address.address = "192.168.1.3"
    assert interface_wo_address.address == as_address("192.168.1.3")


def test_set_address_fail(interface_wo_address):
    with pytest.raises(ValueError):
        interface_wo_address.address = as_address("192.168.0.4")


def test_list_forwardings_unconnected(interface_wo_address):
    assert list(interface_wo_address.forwardings) == [Local(CIDR_LOCAL)]


def test_list_forwardings_non_trivial(interface_wo_address):
    interface_wo_address.forwardings = [Relay("192.168.1.1", "0.0.0.0/0")]
    assert list(interface_wo_address.forwardings) == [Local(CIDR_LOCAL), Relay("192.168.1.1")]
