from itsim.network.route import Local, Relay
from itsim.network.location import Location
from itsim.network.packet import Packet
from itsim.types import AddressRepr, as_address


def packet(address_dest: AddressRepr) -> Packet:
    return Packet(Location("192.168.1.45", 9887), Location(address_dest, 443), 1080)


def test_local():
    f = Local("192.168.1.0/24")
    assert f.get_hop(as_address("192.168.1.89")) == as_address("192.168.1.89")


def test_relay():
    f = Relay("192.168.1.2", "0.0.0.0/0")
    assert f.get_hop(as_address("2.3.89.2")) == as_address("192.168.1.2")
