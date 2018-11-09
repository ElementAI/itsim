import pytest

from greensim.random import constant
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
    return Interface(link)


def test_set_address(interface_wo_address):
    interface_wo_address.address = "192.168.1.3"
    assert interface_wo_address.address == as_address("192.168.1.3")


def test_set_address_fail(interface_wo_address):
    with pytest.raises(ValueError):
        interface_wo_address.address = as_address("192.168.0.4")
