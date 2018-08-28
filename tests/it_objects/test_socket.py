from itsim.it_objects.location import Location
from itsim.it_objects.packet import Packet
from itsim.it_objects.payload import Payload
from itsim.network import Network
from itsim.node import Node, Socket
from itsim.types import as_address

from pytest import fixture

from queue import Queue

LINKED_ADDRESS = as_address("54.88.73.99")

class NetworkMock(Network):
    
    def __init__(self):
        self.transmit_called_with = None

    def transmit(self, packet: Packet):
        self.transmit_called_with = packet

    def link(self, node, *args):
        return LINKED_ADDRESS


@fixture
def loc_a():
    return Location("54.88.73.99", 443)


@fixture
def loc_b():
    return Location("132.204.8.144", 80)


@fixture
def node():
    node = Node()
    node.link_to(NetworkMock())
    return node


@fixture
def socket(loc_a, loc_b, node):
    return Socket(loc_a, loc_b, node)

@fixture
def packet(loc_a, loc_b):
    return Packet(loc_a, loc_b, 1, Payload())


def test_constructor(loc_a, loc_b, node):
    socket = Socket(loc_a, loc_b, node)
    assert socket._src == loc_a
    assert socket._dest == loc_b
    assert socket._node == node
    assert isinstance(socket._payload_queue, Queue)
    assert socket._payload_queue.empty()


def test_send(socket, packet):
    socket.send(packet.payload, packet.byte_size)
    assert packet == socket._node._networks[LINKED_ADDRESS].network.transmit_called_with


def test_enqueue(socket):
    assert socket._payload_queue.empty()
    pay = Payload()
    socket.enqueue(pay)
    assert socket._payload_queue.get() == pay
    assert socket._payload_queue.empty()

def test_recv(socket):
    assert socket.recv() is None
    pay = Payload()
    socket.enqueue(pay)
    assert socket.recv() == pay
    assert socket.recv() is None
