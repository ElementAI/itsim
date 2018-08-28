from itsim.it_objects.location import Location
from itsim.it_objects.packet import Packet
from itsim.it_objects.payload import Payload
from itsim.node import Socket

from pytest import fixture

from queue import Queue

from unittest.mock import patch


@fixture
def loc_a():
    return Location("54.88.73.99", 443)


@fixture
def loc_b():
    return Location("132.204.8.144", 80)


@fixture
@patch("itsim.node.Node")
def socket(mock_node, loc_a):
    return Socket(loc_a, mock_node)


@fixture
def packet(loc_a, loc_b):
    return Packet(loc_a, loc_b, 1, Payload())


@patch("itsim.node.Node")
def test_constructor(mock_node, loc_a):
    socket = Socket(loc_a, mock_node)
    assert socket._src == loc_a
    assert socket._node == mock_node
    assert isinstance(socket._payload_queue, Queue)
    assert socket._payload_queue.empty()


def test_send(socket, loc_a, loc_b, packet):
    socket.send(loc_b, packet.byte_size, packet.payload)
    socket._node._send_to_network.assert_called_with(packet)


def test_enqueue(socket):
    assert socket._payload_queue.empty()
    pay = Payload()
    socket._enqueue(pay)
    assert socket._payload_queue.get() == pay
    assert socket._payload_queue.empty()


def test_recv(socket):
    assert socket.recv() is None
    pay = Payload()
    socket._enqueue(pay)
    assert socket.recv() == pay
    assert socket.recv() is None
