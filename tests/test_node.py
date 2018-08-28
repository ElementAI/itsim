from greensim import Process, Simulator

from itsim.it_objects.location import Location
from itsim.it_objects.packet import Packet
from itsim.it_objects.payload import Payload
from itsim.node import Node, NoNetworkLinked, PortAlreadyInUse, SocketAlreadyOpen
from itsim.network import InvalidAddress
from itsim.types import as_address

from pytest import fixture, raises

from unittest.mock import patch


@fixture
def loc_a():
    return Location("54.88.73.99", 443)


@fixture
def loc_b():
    return Location("132.204.8.144", 80)


BROADCAST_ADDR = as_address("132.216.177.160")


@fixture
@patch("itsim.network.Network")
def node(mock_net, loc_a):
    node = Node()
    mock_net.link.return_value = loc_a.host_as_address()
    mock_net.address_broadcast = BROADCAST_ADDR
    node.link_to(mock_net, loc_a.host)
    return node


@fixture
def packet(loc_a, loc_b):
    return Packet(loc_a, loc_b, 1, Payload())


@fixture
def reverse_packet(loc_a, loc_b):
    return Packet(loc_b, loc_a, 1, Payload())


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
            assert node._networks[loc_a.host_as_address()].ports[loc_a.port].local.name == Process.current().local.name
            assert loc_a == src

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


def test_open_socket(loc_a, loc_b, node):

    def socket_check():
        with node.bind(loc_a) as src:
            with node.open_socket(src, loc_b) as sock:
                assert node._sockets[src] == sock

    run_test_sim(socket_check)


def test_no_network(loc_a, loc_b, node):

    def socket_check():
        with raises(NoNetworkLinked):
            with node.open_socket(loc_a, loc_b):
                pass

    run_test_sim(socket_check)


def test_unlinked_port(loc_a, loc_b, node):

    def socket_check():
        with node.bind(loc_a):
            loc_a._port = 80
            with raises(NoNetworkLinked):
                with node.open_socket(loc_a, loc_b):
                    pass

    run_test_sim(socket_check)


def test_socket_in_use(loc_a, loc_b, node):

    def socket_check():
        with node.bind(loc_a) as src:
            with node.open_socket(src, loc_b):
                with raises(SocketAlreadyOpen):
                    with node.open_socket(src, loc_b):
                        pass

    run_test_sim(socket_check)


def test_receive(loc_a, loc_b, node, reverse_packet):

    def recv_check():
        with node.bind(loc_a) as src:
            with node.open_socket(src, loc_b) as sock:
                node._receive(reverse_packet)
                assert sock.recv() == reverse_packet

    run_test_sim(recv_check)


def test_receive_no_socket(loc_a, loc_b, node, packet):

    def recv_check():
        with node.bind(loc_a) as src:
            with node.open_socket(src, loc_b) as sock:
                # Locations are reversed. Packet should be dropped
                node._receive(packet)
                assert sock._packet_queue.empty()

    run_test_sim(recv_check)


def test_send_to_network(node, packet):

    def send_check():
        with node.bind(packet.source):
            node._send_to_network(packet)
            node._networks[packet.source.host_as_address()].network.transmit.assert_called_with(packet)

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
    assert BROADCAST_ADDR == node._get_network_broadcast_address(loc_a.host)


def test_get_broadcast_from_unlinked_network(node, loc_b):
    with raises(NoNetworkLinked):
        node._get_network_broadcast_address(loc_b.host)
