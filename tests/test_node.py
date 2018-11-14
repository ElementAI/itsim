import random
from unittest.mock import patch, call

import pytest

from greensim.random import constant
from itsim.machine.endpoint import Endpoint
from itsim.machine.node import Socket, PortAlreadyInUse, NameNotFound
from itsim.network.forwarding import Relay
from itsim.network.link import Link
from itsim.network.location import Location
from itsim.network.packet import Packet, Payload, PayloadDictionaryType
from itsim.types import as_cidr, as_address, AddressRepr, Hostname, as_hostname, Address


def addr(*ar: AddressRepr):
    return [as_address(a) for a in ar]


def test_socket_resolve_destination_address():
    socket = Socket(9887, None)
    assert socket._resolve_destination_final(as_hostname("192.168.3.8")) == as_address("192.168.3.8")


def test_socket_resolve_destination_hostsname():
    class NodeFakingResolution:
        def resolve_name(self, name: str) -> Address:
            if name == "hoho.com":
                return as_address("45.67.89.12")
            raise ValueError()
    socket = Socket(9887, NodeFakingResolution())
    assert socket._resolve_destination_final(as_hostname("hoho.com")) == as_address("45.67.89.12")


@pytest.fixture
def endpoint():
    return Endpoint()


CIDR_SMALL = as_cidr("192.168.1.0/24")
CIDR_LARGE = as_cidr("10.10.128.0/17")


@pytest.fixture
def link_small():
    return Link(CIDR_SMALL, constant(0), constant(0))


@pytest.fixture
def link_large():
    return Link(CIDR_LARGE, constant(0), constant(0))


def test_node_unconnected(endpoint):
    assert list(endpoint.addresses()) == addr("127.0.0.1")


ADDRESS_SMALL = CIDR_SMALL.network_address + 4
ADDRESS_LARGE = as_address("10.10.192.54")


@pytest.fixture
def endpoint_2links(endpoint, link_small, link_large):
    return endpoint.connected_to(link_small, 4).connected_to(link_large, ADDRESS_LARGE, [Relay("10.10.128.1")])


def test_node_addresses(endpoint_2links):
    assert list(endpoint_2links.addresses()) == addr("127.0.0.1", ADDRESS_SMALL, ADDRESS_LARGE)


def test_is_port_free_limits(endpoint):
    for port in [0, 65535]:
        assert not endpoint.is_port_free(port)


def test_is_port_free(endpoint):
    for n in range(2000):
        assert endpoint.is_port_free(random.randint(1, 65534))


def exercise_free_port_sampling(endpoint):
    for n in range(2000):
        port = endpoint._sample_port_unprivileged_free()
        assert port >= 1024
        assert endpoint.is_port_free(port)


def test_sample_free_port_no_socket(endpoint):
    exercise_free_port_sampling(endpoint)


@pytest.fixture
def socket80(endpoint):
    assert endpoint.is_port_free(80)
    return endpoint.bind(80)


def test_socket_state(endpoint, socket80):
    assert socket80.port == 80
    assert not socket80.is_closed
    assert not endpoint.is_port_free(80)
    socket80.close()
    assert socket80.is_closed
    assert endpoint.is_port_free(80)
    with pytest.raises(ValueError):
        socket80.port


def test_socket_context_manager(socket80):
    assert not socket80.is_closed
    with socket80:
        assert not socket80.is_closed
    assert socket80.is_closed


def test_sample_free_port_after_reservations(endpoint):
    PORTS_RESERVED = [9887, 80, 65000, 45454, 12345]
    sockets = []
    try:
        sockets = [endpoint.bind(port) for port in PORTS_RESERVED]
        for port in PORTS_RESERVED:
            assert not endpoint.is_port_free(port)
        exercise_free_port_sampling(endpoint)
    finally:
        for socket in sockets:
            socket.close()


def test_bind_port_used(endpoint, socket80):
    with socket80:
        with pytest.raises(PortAlreadyInUse):
            with endpoint.bind(80) as socket_other:
                pytest.fail()


@pytest.fixture
def endpoint_fakesend():
    class FakeSendPacket(Endpoint):
        packets_sent = []

        def _send_packet(self, packet: Packet) -> None:
            self.packets_sent.append(packet)

        def check_packets_sent(self, *packets_expected: Packet) -> None:
            assert list(
                Packet(Location(hn_src, port_src), Location(hn_dest, port_dest), num_bytes, Payload(entries))
                for (hn_src, port_src), (hn_dest, port_dest), num_bytes, entries in packets_expected
            ) == self.packets_sent

    return FakeSendPacket()


def test_send_packet_address(endpoint):
    with patch.object(endpoint, "_send_packet") as mock:
        with endpoint.bind(9887) as socket:
            socket.send(("172.99.80.23", 80), 45666)
        with endpoint.bind(53) as socket:
            socket.send(("8.8.8.8", 53), 652, Payload({PayloadDictionaryType.CONTENT: "google.ca"}))
        mock.assert_has_calls(
            [
                call(Packet(Location(None, 9887), Location("172.99.80.23", 80), 45666, Payload({}))),
                call(
                    Packet(
                        Location(None, 53),
                        Location("8.8.8.8", 53),
                        652,
                        Payload({PayloadDictionaryType.CONTENT: "google.ca"})
                    )
                )
            ]
        )


def test_resolve_destination_final_address(socket80):
    for s in ["8.8.8.8", "192.168.1.8"]:
        assert socket80._resolve_destination_final(as_hostname(s)) == as_address(s)


def test_resolve_destination_final_address(endpoint, socket80):
    with socket80:
        with patch.object(endpoint, "resolve_name", return_value=as_address("172.99.0.2")) as mock:
            assert isinstance(socket80._resolve_destination_final(as_hostname("google.ca")), Address)
            mock.assert_called_once_with("google.ca")
        with patch.object(endpoint, "resolve_name", side_effect=NameNotFound("asdf")) as mock:
            with pytest.raises(NameNotFound):
                socket80._resolve_destination_final(as_hostname("asdf"))
            mock.assert_called_once_with("asdf")


def test_send_packet_hostname(endpoint):
    with patch.object(endpoint, "resolve_name", return_value="172.99.0.2"), \
            patch.object(endpoint, "_send_packet") as mock:
        with endpoint.bind(9887) as socket:
            socket.send(("google.ca", 443), 3398)
        mock.assert_called_once_with(Packet(Location(None, 9887), Location("172.99.0.2", 443), 3398, Payload({})))


def test_recv(socket80):
    pytest.fail()


def test_recv_socket_closed(socket80):
    pytest.fail()
