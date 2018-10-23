from greensim import add, now, Simulator
from greensim.random import constant

from itsim.it_objects.endpoint import Endpoint
from itsim.it_objects.location import Location
from itsim.it_objects.packet import Packet
from itsim.it_objects.payload import Payload, PayloadDictionaryType
from itsim.network import Network

from pytest import fixture


@fixture
def loc_a():
    return Location("54.88.73.99", 443)


@fixture
def loc_b():
    return Location("132.204.8.144", 80)


@fixture
def loc_c():
    return Location("132.216.177.160", 25)


@fixture
def two_node_setup(loc_a, loc_b):
    simulator = Simulator()
    net = Network(simulator,
                  cidr="0.0.0.0/0",
                  bandwidth=constant(1),
                  latency=constant(5),
                  num_skip_addresses=100)
    end_a = Endpoint("Antigonish", net, loc_a.hostname)
    end_b = Endpoint("Bathurst", net, loc_b.hostname)
    return (simulator, net, end_a, end_b, loc_a, loc_b)


# Test that a packet can be sent through the network and back and received on both ends
# Also verifies the time delay of the transmission
def test_packet_bounce(two_node_setup):
    sim, net, end_a, end_b, loc_a, loc_b = two_node_setup

    flag = 0
    payload_a = Payload({PayloadDictionaryType.CONTENT: end_a.name})
    payload_b = Payload({PayloadDictionaryType.CONTENT: end_b.name})
    packet_a = Packet(loc_a, loc_b, 10, payload_a)
    packet_b = Packet(loc_b, loc_a, 0, payload_b)

    def listen_a():
        nonlocal flag
        with end_a.open_socket(loc_a) as sock:
            assert packet_b == sock.recv()
            sock.send(loc_b, 10, payload_a)
            flag += 1
            # Packet with zero length is bound by latency
            assert 5 == now()

    def listen_b():
        nonlocal flag
        with end_b.open_socket(loc_b) as sock:
            sock.send(loc_a, 0, payload_b)
            assert packet_a == sock.recv()
            flag += 1
            # Packet with finite length is bound by latency and bandwidth
            assert 20 == now()

    def controller():
        add(listen_a)
        add(listen_b)

    sim.add(controller)
    sim.run()
    assert 2 == flag


@fixture
def three_node_setup(two_node_setup, loc_c):
    sim, net, end_a, end_b, loc_a, loc_b = two_node_setup
    end_c = Endpoint("Chicoutimi", net, loc_c.hostname)
    return (sim, net, end_a, end_b, end_c, loc_a, loc_b, loc_c)


# Test Packets going from C -> B -> A -> C
# This proves Packets are not intercepted by whatever is on the network
# The time checks verify the order of Packet transmission
def test_packet_cycle(three_node_setup):
    sim, net, end_a, end_b, end_c, loc_a, loc_b, loc_c = three_node_setup

    flag = 0
    payload_a = Payload({PayloadDictionaryType.CONTENT: end_a.name})
    payload_b = Payload({PayloadDictionaryType.CONTENT: end_b.name})
    payload_c = Payload({PayloadDictionaryType.CONTENT: end_c.name})
    packet_a = Packet(loc_a, loc_c, 0, payload_a)
    packet_b = Packet(loc_b, loc_a, 0, payload_b)
    packet_c = Packet(loc_c, loc_b, 0, payload_c)

    def listen_a():
        nonlocal flag
        with end_a.open_socket(loc_a) as sock:
            assert packet_b == sock.recv()
            sock.send(loc_c, 0, payload_a)
            flag += 1
            assert 10 == now()

    def listen_b():
        nonlocal flag
        with end_b.open_socket(loc_b) as sock:
            assert packet_c == sock.recv()
            sock.send(loc_a, 0, payload_b)
            flag += 1
            assert 5 == now()

    def listen_c():
        nonlocal flag
        with end_c.open_socket(loc_c) as sock:
            sock.send(loc_b, 0, payload_c)
            assert packet_a == sock.recv()
            flag += 1
            assert 15 == now()

    def controller():
        add(listen_a)
        add(listen_b)
        add(listen_c)

    sim.add(controller)
    sim.run()
    assert 3 == flag


def test_packet_broadcast(three_node_setup):
    sim, net, end_a, end_b, end_c, loc_a, loc_b, loc_c = three_node_setup

    flag = 0
    payload_c = Payload({PayloadDictionaryType.CONTENT: end_c.name})
    packet_c = Packet(loc_c, Location(net.address_broadcast, 1867), 0, payload_c)

    def listen_a():
        nonlocal flag
        with end_a.open_socket(Location(loc_a.hostname, 1867)) as sock:
            assert packet_c == sock.recv()
            flag += 1
            assert 5 == now()

    def listen_b():
        nonlocal flag
        with end_b.open_socket(Location(loc_b.hostname, 1867)) as sock:
            assert packet_c == sock.recv()
            flag += 1
            assert 5 == now()

    def listen_c():
        nonlocal flag
        with end_c.open_socket(loc_c) as sock:
            sock.broadcast(1867, 0, payload_c)
            flag += 1

    def controller():
        add(listen_a)
        add(listen_b)
        add(listen_c)

    sim.add(controller)
    sim.run()
    assert 3 == flag
