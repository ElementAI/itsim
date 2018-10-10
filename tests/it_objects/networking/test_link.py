from collections import OrderedDict

from greensim.random import expo, normal

from itsim.it_objects import ITSimulator
from itsim.it_objects.networking.link import AddressInUse, Link
from itsim.node import Node
from itsim.types import as_address

from pytest import fixture, raises

from unittest.mock import patch


@fixture
def link():
    return Link(ITSimulator(), expo(10), normal(10, 1))


def test_init():
    bandwidth = expo(10)
    latency = normal(10, 1)
    sim = ITSimulator()
    guinea = Link(sim, bandwidth, latency)
    assert sim == guinea.sim
    assert bandwidth == guinea._bandwidth
    assert latency == guinea._latency
    assert OrderedDict() == guinea._nodes


def test_add(link):
    node_a, node_b = Node(), Node()
    addr_a, addr_b = "54.88.73.99", "132.204.8.144"
    link.add_node(node_a, addr_a)
    link.add_node(node_b, addr_b)
    assert node_a == link._nodes[as_address(addr_a)]()
    assert node_b == link._nodes[as_address(addr_b)]()


def test_same(link):
    node = Node()
    addr_a, addr_b = "54.88.73.99", "132.204.8.144"
    link.add_node(node, addr_a)
    link.add_node(node, addr_b)
    assert node == link._nodes[as_address(addr_a)]()
    assert node == link._nodes[as_address(addr_b)]()


def test_add_twice(link):
    node = Node()
    addr = "54.88.73.99"
    link.add_node(node, addr)
    with raises(AddressInUse):
        link.add_node(node, addr)


def test_drop(link):
    node_a, node_b = Node(), Node()
    addr_a, addr_b = "54.88.73.99", "132.204.8.144"
    link.add_node(node_a, addr_a)
    link.add_node(node_b, addr_b)
    assert link.drop_node(addr_a)
    assert as_address(addr_a) not in link._nodes
    assert node_b == link._nodes[as_address(addr_b)]()


def test_drop_twice(link):
    node = Node()
    addr = "54.88.73.99"
    link.add_node(node, addr)
    # Drop returns whether or not the node was dropped. It does not fail
    assert link.drop_node(addr)
    assert not link.drop_node(addr)


@patch("itsim.it_objects.ITSimulator")
@patch("itsim.it_objects.packet.Packet")
def test_transmit(mock_sim, mock_pack):
    guinea = Link(mock_sim, expo(10), normal(10, 1))
    guinea.transmit(mock_pack, Node())
    mock_sim.add.assert_called_once()
    # Very crude type check since we don't have the underlying function worked out in detail
    assert hasattr(mock_sim.add.call_args[0][0], '__call__')
