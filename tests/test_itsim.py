from ipaddress import ip_address

import pytest

from itsim import as_address, as_port


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
