from itsim.network.location import Location
from itsim.network.packet import Packet


def test_packet_with_source():
    orig = Packet(Location(None, 9887), Location("1.2.3.4", 443), 8997, {"asdf": "qwerty"})
    new = orig.with_address_source("192.168.1.34")
    assert new == Packet(Location("192.168.1.34", orig.source.port), orig.dest, orig.byte_size, orig.payload)
