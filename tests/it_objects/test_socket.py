from itsim.it_objects.location import Location
from itsim.it_objects.packet import Packet
from itsim.it_objects.payload import Payload
from itsim.node import Socket

from greensim import add, advance, local, Simulator

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


@fixture
def payload():
    return Payload()


@patch("itsim.node.Node")
def test_constructor(mock_node, loc_a):
    socket = Socket(loc_a, mock_node)
    assert socket._src == loc_a
    assert socket._node == mock_node
    assert isinstance(socket._packet_queue, Queue)
    assert socket._packet_queue.empty()
    assert not socket._packet_signal.is_on


def test_send(socket, loc_a, loc_b, packet):
    socket.send(loc_b, packet.byte_size, packet.payload)
    socket._node._send_to_network.assert_called_with(packet)


def test_enqueue(socket, packet):
    assert socket._packet_queue.empty()
    socket._enqueue(packet)
    assert socket._packet_signal.is_on
    assert socket._packet_queue.get() == packet
    assert socket._packet_queue.empty()


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


def test_recv(socket, packet):

    socket._enqueue(packet)

    def recv_test():
        assert packet == socket.recv()

    run_test_sim(recv_test)


def test_recv_wait(socket, packet):

    seeker_string = "Looking for a packet"

    def seeker():
        local.name = seeker_string
        assert packet == socket.recv()

    def wait_and_see():
        add(seeker)
        advance(1)
        # Show that the correct Process is waiting
        assert seeker_string == socket._packet_signal._queue.peek().local.name
        socket._enqueue(packet)
        assert 1 == socket._packet_queue.qsize()
        advance(1)
        # Show that the process pulled the packet
        assert socket._packet_queue.empty()

    run_test_sim(wait_and_see)


def test_recv_multiple_waits(socket, loc_a, loc_b):

    packets = [Packet(loc_a, loc_b, 0, Payload()),
               Packet(loc_a, loc_b, 1, Payload())]

    # Allows for testing order in the queue
    def create_seeker(n):
        def seeker():
            local.name = n
            assert packets[n] == socket.recv()
        return seeker

    def wait_and_see():
        add(create_seeker(0))
        add(create_seeker(1))
        advance(1)

        # Show that the correct Process is first
        assert 0 == socket._packet_signal._queue.peek().local.name
        assert 2 == len(socket._packet_signal._queue)
        socket._enqueue(packets[0])
        advance(1)

        # Show that there is still one process waiting
        assert 1 == socket._packet_signal._queue.peek().local.name
        assert 1 == len(socket._packet_signal._queue)
        socket._enqueue(packets[1])
        advance(1)

        # Show that the process pulled the packet
        assert socket._packet_queue.empty()

    run_test_sim(wait_and_see)
