from contextlib import contextmanager
import enum
import gc
from unittest.mock import call, Mock, patch

import pytest

from greensim import advance
from greensim.random import constant

from itsim.machine.endpoint import Endpoint
from itsim.machine.node import PortAlreadyInUse, PORT_EPHEMERAL_MIN, PORT_EPHEMERAL_UPPER, PORT_MAX, PORT_NULL, \
    EphemeralPortsAllInUse, NoRouteToHost
from itsim.machine.socket import Timeout, Socket
from itsim.network.route import Relay
from itsim.network.link import Link
from itsim.network.location import Location
from itsim.network.packet import Packet
from itsim.network.service.dhcp.client import DHCPClient
from itsim.simulator import Simulator
from itsim.types import as_cidr, as_address, AddressRepr, as_hostname, Protocol


def addr(*ar: AddressRepr):
    return [as_address(a) for a in ar]


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
    for port in range(PORT_NULL + 1, PORT_MAX):
        assert endpoint.is_port_free(port)


def test_get_port_ephemeral(endpoint):
    for expected in range(PORT_EPHEMERAL_MIN, PORT_EPHEMERAL_UPPER):
        port = endpoint._get_port_ephemeral()
        assert expected == port
    assert PORT_EPHEMERAL_MIN == endpoint._get_port_ephemeral()  # Cycle when reaching last.


def test_raise_once_no_more_port_ephemeral(endpoint):
    sockets = [endpoint.bind(Protocol.NONE, port) for port in range(PORT_EPHEMERAL_MIN, PORT_EPHEMERAL_UPPER)]
    try:
        with pytest.raises(EphemeralPortsAllInUse):
            with endpoint.bind():
                pass
    finally:
        for sock in sockets:
            sock.close()


@pytest.fixture
def socket80(endpoint):
    assert endpoint.is_port_free(80)
    return endpoint.bind(Protocol.TCP, 80)


def test_socket_state(endpoint, socket80):
    assert socket80.port == 80
    assert not socket80.is_closed
    assert not endpoint.is_port_free(80)
    socket80.close()
    assert socket80.is_closed
    assert endpoint.is_port_free(80)


def test_socket_context_manager(socket80):
    assert not socket80.is_closed
    with socket80:
        assert not socket80.is_closed
    assert socket80.is_closed


def test_ephemeral_port_after_reservations(endpoint):
    PORTS_RESERVED = [9887, 80, 65000, 45454, PORT_EPHEMERAL_MIN, PORT_EPHEMERAL_UPPER - 1, 12345]
    sockets = []
    try:
        sockets = [endpoint.bind(Protocol.NONE, port) for port in PORTS_RESERVED]
        for port in PORTS_RESERVED:
            assert not endpoint.is_port_free(port)
        for expected in range(PORT_EPHEMERAL_MIN, PORT_EPHEMERAL_UPPER):
            if expected not in PORTS_RESERVED:
                port = endpoint._get_port_ephemeral()
                assert endpoint.is_port_free(port)
    finally:
        for socket in sockets:
            socket.close()


def test_bind_port_used(endpoint, socket80):
    with socket80:
        with pytest.raises(PortAlreadyInUse):
            # The last next expression must raise the exception, otherwise the test is failed. In the latter case, since
            # the fixtures are abandoned after the execution of the test, it's ok not to leave on the test failure
            # exception without having closed the unduly-instantiated socket instance. However, in practice, sockets
            # must always be closed, lest ports are leaked.
            sock = endpoint.bind(Protocol.TCP, 80)
            pytest.fail()
            sock.close()  # Do something with the socket to avoid being called out for PEP-8 non-conformance.


def test_send_packet_address(endpoint):
    with patch.object(endpoint, "_send_packet") as mock:
        with endpoint.bind(Protocol.TCP, 9887) as socket:
            socket.send(("172.99.80.23", 80), 45666)
        with endpoint.bind(Protocol.UDP, 53) as socket:
            socket.send(("8.8.8.8", 53), 652, {"content": "google.ca"})
        mock.assert_has_calls(
            [
                call(9887, Location("172.99.80.23", 80), 45666, {}),
                call(53, Location("8.8.8.8", 53), 652, {"content": "google.ca"})
            ]
        )


def test_resolve_destination_address(endpoint):
    for s in ["8.8.8.8", "192.168.1.8"]:
        assert endpoint.resolve_name(as_hostname(s)) == as_address(s)


def test_send_packet_hostname(endpoint):
    with patch.object(endpoint, "resolve_name", return_value="172.99.0.2"), \
            patch.object(endpoint, "_send_packet") as mock:
        with endpoint.bind(Protocol.TCP, 9887) as socket:
            socket.send(("google.ca", 443), 3398)
        mock.assert_called_once_with(9887, Location("172.99.0.2", 443), 3398, {})


@contextmanager
def run_simulation_receiving(socket, delay_recv, expected_end_time):
    packet_sent = Packet(
        Location("192.168.2.89", 9887),
        Location("172.99.0.2", 443),
        12345,
        {"content": "Hello recv!"}
    )
    packet_received = None

    def receiving_on_endpoint():
        nonlocal packet_received
        packet_received = socket.recv()

    def enqueue_packet():
        advance(delay_recv)
        socket._enqueue(packet_sent)

    sim = Simulator()
    sim.add(receiving_on_endpoint)
    sim.add(enqueue_packet)
    yield sim

    try:
        sim.run()
        assert packet_received == packet_sent
    finally:
        assert sim.now() == pytest.approx(expected_end_time)


def test_recv(socket80):
    with run_simulation_receiving(socket80, 100.0, 100.0):
        pass


def test_recv_socket_closed_in_setup(socket80):
    socket80.close()
    with pytest.raises(ValueError):
        with run_simulation_receiving(socket80, 100.0, 0):
            pass


def test_recv_socket_closed_during_sim(socket80):
    def do_close():
        advance(50)
        socket80.close()

    with pytest.raises(ValueError):
        with run_simulation_receiving(socket80, 100.0, 50.0) as sim:
            sim.add(do_close)


@enum.unique
class SimulationResult(enum.Enum):
    INCOMPLETE = enum.auto()
    COMPLETE = enum.auto()
    TIMEOUT = enum.auto()


def run_simulation_timeout(socket, timeout):
    packet = Packet(Location("192.168.2.89", 9887), Location("172.99.0.2", 443), 12345)
    ret_value = SimulationResult.INCOMPLETE

    def receive():
        nonlocal ret_value
        try:
            pkt_received = socket.recv(timeout)
            assert pkt_received == packet
            ret_value = SimulationResult.COMPLETE
        except Timeout:
            ret_value = SimulationResult.TIMEOUT

    def enqueue():
        advance(100)
        socket._enqueue(packet)

    sim = Simulator()
    sim.add(receive)
    sim.add(enqueue)
    sim.run()
    return ret_value


def test_recv_socket_timeout_none(socket80):
    assert run_simulation_timeout(socket80, 1000) == SimulationResult.COMPLETE


def test_recv_socket_timeout_fired(socket80):
    assert run_simulation_timeout(socket80, 50) == SimulationResult.TIMEOUT


def test_send_packet(endpoint_2links, link_small, link_large):
    for source, dest, link, relay in [
        (ADDRESS_SMALL, "192.168.1.67", link_small, "192.168.1.67"),
        (ADDRESS_LARGE, "10.10.192.245", link_large, "10.10.192.245"),
        (ADDRESS_LARGE, "172.92.0.2", link_large, "10.10.128.1")
    ]:
        with patch.object(link, "_transfer_packet") as mock:
            loc_dest = Location(dest, 443)
            endpoint_2links._send_packet(9887, loc_dest, 1234, {})
            mock.assert_called_with(Packet(Location(source, 9887), loc_dest, 1234, {}), as_address(relay))


def test_solve_transfer_local(endpoint_2links):
    for address_r, cidr_r in [("192.168.1.23", CIDR_SMALL), ("10.10.192.78", CIDR_LARGE)]:
        address = as_address(address_r)
        interface, hop = endpoint_2links._solve_transfer(address)
        assert interface.cidr == as_cidr(cidr_r)
        assert hop == address


def test_solve_transfer_beyond(endpoint_2links):
    interface, hop = endpoint_2links._solve_transfer(as_address("172.99.0.2"))
    assert interface.cidr == as_cidr("10.10.128.0/17")
    assert hop == as_address("10.10.128.1")


def test_solve_transfer_no_route(endpoint, link_small):
    endpoint.connected_to(link_small, 88, [Relay("192.168.1.2", "10.0.0.0/8")])
    with pytest.raises(NoRouteToHost):
        endpoint._solve_transfer(as_address("172.99.0.2"))


@pytest.fixture
def socket9887(endpoint_2links):
    return endpoint_2links.bind(Protocol.TCP, 9887)


def do_test_receive_packet(endpoint, socket, loc_dest):
    packet = Packet(Location(None, 42345), Location.from_repr(loc_dest), 123456)
    with socket:
        endpoint._receive_packet(packet)
    return packet


def test_receive_packet_port_bound(endpoint_2links, socket9887):
    with patch.object(socket9887, "_enqueue") as mock:
        packet = do_test_receive_packet(endpoint_2links, socket9887, (ADDRESS_LARGE, 9887))
        mock.assert_called_with(packet)


def test_packet_receive_broadcast_port_bound(endpoint_2links, socket9887):
    with patch.object(socket9887, "_enqueue") as mock:
        packet = do_test_receive_packet(endpoint_2links, socket9887, (CIDR_LARGE.broadcast_address, 9887))
        mock.assert_called_with(packet)


def test_receive_packet_port_unbound(endpoint_2links, socket9887):
    with patch.object(endpoint_2links, "drop_packet") as mock:
        packet = do_test_receive_packet(endpoint_2links, socket9887, (ADDRESS_LARGE, 80))
        mock.assert_called_with(packet)


def test_receive_packet_in_transit(endpoint_2links, socket9887):
    with patch.object(endpoint_2links, "handle_packet_transit") as mock:
        packet = do_test_receive_packet(endpoint_2links, socket9887, (ADDRESS_LARGE + 1, 9887))
        mock.assert_called_with(packet)


def test_packet_broadcast_alone_on_link(endpoint, link_small):
    endpoint.connected_to(link_small, "192.168.1.100")
    with patch.object(link_small, "_transfer_packet") as mock:
        with endpoint.bind() as socket:
            socket.send(("192.168.1.255", 9887), 1234)
            mock.assert_called_with(
                Packet(Location("192.168.1.100", socket.port), Location("192.168.1.255", 9887), 1234),
                as_address("192.168.1.255")
            )


class FakeSocket(Socket):
    num_close = 0

    def __init__(self, protocol, port, node, as_pid):
        super().__init__(protocol, port, node, as_pid)

    def close(self):
        super().close()
        FakeSocket.num_close += 1


def test_socket_lost_should_be_closed(endpoint):
    with patch("itsim.machine.node.Socket", FakeSocket):
        socket = endpoint.bind(Protocol.NONE, 9887)
        assert not socket.is_closed
        assert not endpoint.is_port_free(9887)
        socket = None
        gc.collect()
        assert endpoint.is_port_free(9887)
        assert FakeSocket.num_close == 1


def test_connected_to_with_dhcp(endpoint, link_small):
    endpoint.schedule_daemon_in = Mock()

    endpoint.connected_to(link_small, 88, [Relay("192.168.1.2", "10.0.0.0/8")])
    endpoint.schedule_daemon_in.assert_not_called()

    sim = Simulator()
    endpoint.connected_with_dhcp(link_small, sim, 88, [Relay("192.168.1.2", "10.0.0.0/8")])
    endpoint.schedule_daemon_in.assert_called_once()
    _, args, _ = endpoint.schedule_daemon_in.mock_calls[0]
    assert sim == args[0]
    assert 0 == args[1]
    # These are sufficient to prove that the DHCPClient was instantiated correctly. Anything more would require adding
    # an __eq__ to the class
    assert isinstance(args[2], DHCPClient)
    assert link_small.cidr == args[2]._interface._link.cidr
