from itsim.network.location import Location
from itsim.network.packet import Packet


src = Location("54.88.73.99", 443)
dest = Location("132.204.8.144", 80)
bigliness = 1e9
payload = {"content": "Good stuff"}


def test_init():
    Packet(src, dest, bigliness, payload)
    Packet(src, dest, bigliness, None)


def test_src():
    assert Packet(src, dest, bigliness, payload).source == Location("54.88.73.99", 443)


def test_dest():
    assert Packet(src, dest, bigliness, payload).dest == Location("132.204.8.144", 80)


def test_byte_size():
    assert Packet(src, dest, bigliness, payload).byte_size == 1e9


def test_payload():
    assert Packet(src, dest, bigliness, payload).payload == payload
    assert Packet(src, dest, bigliness).payload == {}
