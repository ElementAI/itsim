from greensim import Process
from greensim.random import expo, normal

from itsim.simulator import Simulator
from itsim.network import AddressInUse, InvalidAddress, Location, Packet, Payload
from itsim.it_objects.networking.link import Link
from itsim.node import Node, NoNetworkLinked, PortAlreadyInUse
from itsim.types import as_address

from pytest import fixture, raises

from unittest.mock import patch


@fixture
def loc_a():
    return Location("54.88.73.99", 443)


@fixture
def loc_b():
    return Location("132.204.8.144", 80)


@fixture
def link_a():
    return Link(Simulator(), expo(10), normal(10, 1))


@fixture
def link_b():
    return Link(Simulator(), normal(10, 1), expo(10))


BROADCAST_ADDR = as_address("132.216.177.160")


@fixture
@patch("itsim.network.Network")
def node(mock_net, loc_a):
    node = Node()
    mock_net.link.return_value = loc_a.hostname_as_address()
    mock_net.address_broadcast = BROADCAST_ADDR
    node.link_to(mock_net, loc_a.hostname)
    return node


@fixture
def packet(loc_a, loc_b):
    return Packet(loc_a, loc_b, 1, Payload())


@fixture
def reverse_packet(loc_a, loc_b):
    return Packet(loc_b, loc_a, 1, Payload())


@fixture
def broadcast_packet(loc_a, loc_b):
    return Packet(loc_b, Location(BROADCAST_ADDR, loc_a.port), 1, Payload())


@fixture
def link():
    return Link(Simulator(), expo(10), normal(10, 1))


def run_test_sim(fn):
    flag = 0
    sim = Simulator()

    def wrapper():
        nonlocal flag
        fn()
        flag = 1

    sim.add(wrapper)
    sim.run()
    assert 1 == flag


def test_bind(loc_a, node):

    def bind_check():
        with node.bind(loc_a) as src:
            assert node._networks[loc_a.hostname_as_address()].ports[loc_a.port].local.name == \
                Process.current().local.name
            assert loc_a == src

    run_test_sim(bind_check)


def test_bind_releases_on_exception(loc_a, node):

    def bind_check():
        try:
            with node.bind(loc_a):
                raise Exception()
        except Exception:
            assert loc_a.port not in node._networks[loc_a.hostname_as_address()].ports.keys()
            with node.bind(loc_a):
                pass

    run_test_sim(bind_check)


def test_bind_to_invalid_address(loc_b, node):

    def bind_check():
        with raises(InvalidAddress):
            with node.bind(loc_b):
                pass

    run_test_sim(bind_check)


def test_double_bind_fails(loc_a, node):

    def bind_check():
        with node.bind(loc_a):
            with raises(PortAlreadyInUse):
                with node.bind(loc_a):
                    pass

    run_test_sim(bind_check)


def test_open_socket_on_address(node):

    def socket_check():
        src = None
        with node.open_socket("54.88.73.99") as sock:
            src = sock._src
            assert Process.current().local.name == node._networks[as_address("54.88.73.99")] \
                                                       .ports[src._port].local.name
        # Check cleanup
        assert src._port not in node._networks[src.hostname_as_address()].ports.keys()
        assert src not in node._sockets

    run_test_sim(socket_check)


def test_open_socket_on_tuple(node):

    def socket_check():
        src = None
        with node.open_socket(("54.88.73.99", 443)) as sock:
            src = sock._src
            assert Process.current().local.name == node._networks[as_address("54.88.73.99")] \
                                                       .ports[443].local.name
        # Check cleanup
        assert 443 not in node._networks[src.hostname_as_address()].ports.keys()
        assert src not in node._sockets

    run_test_sim(socket_check)


def test_open_socket_on_port(node):

    def socket_check():
        src = None
        with node.open_socket(100) as sock:
            src = sock._src
            assert Process.current().local.name == node._networks[src.hostname_as_address()].ports[100].local.name
        # Check cleanup
        assert 100 not in node._networks[src.hostname_as_address()].ports.keys()
        assert src not in node._sockets

    run_test_sim(socket_check)


def test_open_socket_on_location(loc_a, node):

    def socket_check():
        with node.open_socket(loc_a) as sock:
            assert loc_a == sock._src
            assert Process.current().local.name == \
                node._networks[loc_a.hostname_as_address()].ports[loc_a.port].local.name
        # Check cleanup
        assert loc_a.port not in node._networks[loc_a.hostname_as_address()].ports.keys()
        assert loc_a not in node._sockets

    run_test_sim(socket_check)


def test_open_socket_releases_on_exception(loc_a, node):

    def socket_check():
        try:
            with node.open_socket(loc_a):
                raise Exception()
        except Exception:
            assert loc_a not in node._sockets
            assert node._networks[loc_a.hostname_as_address()].network.address_broadcast not in node._sockets
            with node.open_socket(loc_a):
                pass

    run_test_sim(socket_check)


def test_receive(loc_a, node, reverse_packet):

    def recv_check():
        with node.open_socket(loc_a) as sock:
            node._receive(reverse_packet)
            assert sock.recv() == reverse_packet

    run_test_sim(recv_check)


def test_receive_broadcast(loc_a, node, broadcast_packet):

    def recv_check():
        with node.open_socket(loc_a) as sock:
            node._receive(broadcast_packet)
            assert sock.recv() == broadcast_packet

    run_test_sim(recv_check)


def test_receive_no_socket(loc_a, node, packet):

    def recv_check():
        with node.open_socket(loc_a) as sock:
            # Locations are reversed. Packet should be dropped
            node._receive(packet)
            assert sock._packet_queue.empty()

    run_test_sim(recv_check)


def test_send_to_network(node, packet):

    def send_check():
        with node.bind(packet.source):
            node._send_to_network(packet)
            node._networks[packet.source.hostname_as_address()].network.transmit.assert_called_with(packet)

    run_test_sim(send_check)


def test_send_to_unlinked_network(node, reverse_packet):

    def send_check():
        with node.bind(reverse_packet.dest):
            with raises(NoNetworkLinked):
                node._send_to_network(reverse_packet)

    run_test_sim(send_check)


def test_send_to_unlinked_port(node, packet):

    def send_check():
        with node.bind(packet.source):
            packet.source._port = 80
            with raises(NoNetworkLinked):
                node._send_to_network(packet)

    run_test_sim(send_check)


def test_get_broadcast(node, loc_a):
    assert BROADCAST_ADDR == node._get_network_broadcast_address(loc_a.hostname)


def test_get_broadcast_from_unlinked_network(node, loc_b):
    with raises(NoNetworkLinked):
        node._get_network_broadcast_address(loc_b.hostname)


def test_add_physical_link(node, link_a, link_b):
    node.add_physical_link(link_a, "54.88.73.99")
    node.add_physical_link(link_b, "132.204.8.144")
    assert link_a == node._links["54.88.73.99"]
    assert link_b == node._links["132.204.8.144"]


def test_add_same_physical_link(node, link_a):
    node.add_physical_link(link_a, "54.88.73.99")
    node.add_physical_link(link_a, "132.204.8.144")
    assert link_a == node._links["54.88.73.99"]
    assert link_a == node._links["132.204.8.144"]


def test_add_physical_link_twice(node, link_a, link_b):
    node.add_physical_link(link_a, "54.88.73.99")
    with raises(AddressInUse):
        node.add_physical_link(link_b, "54.88.73.99")


def test_drop_physical_link(node, link_a, link_b):
    node.add_physical_link(link_a, "54.88.73.99")
    node.add_physical_link(link_b, "132.204.8.144")
    assert link_a == node._links["54.88.73.99"]
    assert node.remove_physical_link("132.204.8.144")
    assert "132.204.8.144" not in node._links


def test_drop_same_physical_link(node, link_b):
    node.add_physical_link(link_b, "132.204.8.144")
    assert node.remove_physical_link("132.204.8.144")
    assert not node.remove_physical_link("132.204.8.144")
