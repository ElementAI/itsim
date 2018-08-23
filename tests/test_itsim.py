from ipaddress import ip_address

import pytest

from itsim import Location
from itsim.types import as_address, as_host, as_port


def test_none_as_address():
    assert as_address(None) == ip_address(0)


def test_int_as_address():
    assert as_address(0) == ip_address(0)
    assert as_address(0xc0a80438) == ip_address("192.168.4.56")


def test_int_as_address_nonV4():
    for n in [-1, 2**32]:
        with pytest.raises(ValueError):
            as_address(n)
            pytest.fail()


def test_str_as_address():
    assert as_address("0.0.0.0") == ip_address(0)
    assert as_address("192.168.4.56") == ip_address("192.168.4.56")


def test_address_as_address():
    assert as_address(ip_address(0)) == ip_address(0)
    assert as_address(ip_address("192.168.4.56")) == ip_address("192.168.4.56")


def test_none_as_port():
    assert as_port(None) == 0


def test_int_as_port():
    assert as_port(0) == 0
    assert as_port(9887) == 9887
    assert as_port(65535) == 65535


def test_invalid_int_as_port():
    for n in [-1, 65536]:
        with pytest.raises(ValueError):
            as_port(n)
            pytest.fail()


def test_none_as_host():
    assert as_host(None) == as_address(None)


def test_address_as_host():
    assert as_host("10.1.45.12") == as_address("10.1.45.12")


def test_domain_as_host():
    assert as_host("github.com") == "github.com"


def test_empty_as_host():
    with pytest.raises(ValueError):
        assert as_host("")
        pytest.fail()


def test_location_none_none():
    loc = Location()
    assert loc.host == as_address(None)
    assert loc.port == as_port(None)


def test_location_none_address():
    assert Location(port=9887) == Location(None, 9887)


def test_location_none_port():
    assert Location("192.168.203.1") == Location("192.168.203.1", None)


def test_location_sane():
    loc = Location("calendar.google.com", 9887)
    assert loc.host == as_host("calendar.google.com")
    assert loc.port == as_port(9887)
    assert loc != Location("192.168.203.1", 9087)


def test_location_cmp_sane():
    left = Location("192.168.203.4", 9887)
    right = Location("200.1.1.1", 34)
    assert left < right
    assert not (left > right)
    assert left <= right
    assert not (left >= right)


def test_location_cmp_whatever():
    with pytest.raises(ValueError):
        assert Location("asdf.com", 80) < ("asdf.com", 80)
        pytest.fail()


def test_location_cmp_address_equal():
    assert Location("192.168.203.4", 9000) < Location("192.168.203.4", 9887)


def test_location_cmp_port_equal():
    assert Location("1.2.3.4", 9000) < Location("192.168.203.4", 9000)


def test_location_cmp_same():
    loc = Location("192.45.56.23", 45)
    assert loc == loc
    assert not (loc < loc)


def test_location_eq_whatever():
    with pytest.raises(ValueError):
        assert not Location("asdf.com", 9887) == ("asdf.com", 9887)
        pytest.fail()


def test_location_str():
    assert str(Location("195.78.23.3", 1025)) == "195.78.23.3:1025"


def test_location_repr():
    assert repr(Location("195.78.23.3", 1025)) == repr("195.78.23.3:1025")


def test_location_hash():
    loc = Location("google.ca", 25)
    assert hash(loc) == hash(str(loc))
