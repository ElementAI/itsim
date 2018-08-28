from greensim import Process, Simulator

from itsim.it_objects.location import Location
from itsim.it_objects.packet import Packet
from itsim.it_objects.payload import Payload
from itsim.network import Network
from itsim.node import Node, NoNetworkLinked, PortAlreadyInUse, Socket, SocketAlreadyOpen
from itsim.types import as_address

from pytest import fixture, raises

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
def packet(loc_a, loc_b):
    return Packet(loc_a, loc_b, 1, Payload())


def test_bind(loc_a, node):

    flag = 0
    
    def bind_check():
        nonlocal flag
        with node.bind(loc_a) as src:
            assert node._networks[LINKED_ADDRESS].ports[443].local.name == Process.current().local.name
            assert loc_a == src
            with raises(PortAlreadyInUse):
                with node.bind(loc_a) as src2:
                    pass
        flag = 1

    sim = Simulator()
    sim.add(bind_check)
    sim.run()
    assert 1 == flag
            
def test_open_socket(loc_a, loc_b, node):
    flag = 0
    
    def bind_check():
        nonlocal flag
        with raises(NoNetworkLinked):
            with node.open_socket(loc_a, loc_b) as sock:
                pass
            
        with node.bind(loc_a) as src:
            with node.open_socket(loc_a, loc_b) as sock:
                with raises(SocketAlreadyOpen):
                    with node.open_socket(loc_a, loc_b) as sock2:
                        pass
                assert node._sockets[src] == sock
        flag = 1

    sim = Simulator()
    sim.add(bind_check)
    sim.run()
    assert 1 == flag


def test_receive(loc_a, loc_b, node):
    flag = 0
    packet = Packet(loc_b, loc_a, 1, Payload())
    def bind_check():
        nonlocal flag
            
        with node.bind(loc_a) as src:
            with node.open_socket(loc_a, loc_b) as sock:
                node.receive(packet)
                assert sock.recv() == Payload()
        flag = 1

    sim = Simulator()
    sim.add(bind_check)
    sim.run()
    assert 1 == flag


def test_send_to_network(node, packet):
    node.send_to_network(packet)
    assert packet == node._networks[LINKED_ADDRESS].network.transmit_called_with
