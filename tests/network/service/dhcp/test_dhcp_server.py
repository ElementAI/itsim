from greensim.random import constant
# These tests will actually fail if __init__ is dropped since the Field Enum in
# this file no longer meets the == condition with the one in DHCPServer
# This is a quirk of Python imports that warrants investigation
from itsim.network.service.dhcp.__init__ import DHCP, DHCP_CLIENT_PORT, Field, LEASE_DURATION, RESERVATION_TIME
from itsim.network.service.dhcp.dhcp_server import DHCPServer
from itsim.simulator import Simulator
from itsim.types import as_address, as_cidr

from pytest import fixture

from unittest.mock import Mock, patch

from uuid import uuid4


@fixture
def server():
    return default_server()


# Pytest throws an error if you try and call a fixture directly
def default_server():
    return DHCPServer(2,
                      as_cidr("192.168.1.0/24"),
                      as_address("192.168.1.1"),
                      size_packet_dhcp=constant(1))


def test_init():
    cidr = as_cidr("192.168.1.0/24")
    gateway = as_address("192.168.1.1")
    server = DHCPServer(2,
                        cidr,
                        gateway,
                        size_packet_dhcp=constant(1))
    assert {} == server._address_allocation
    assert {} == server._reserved
    assert cidr == server._cidr
    assert 253 == server._num_hosts_max
    assert as_address("192.168.1.2") == next(server._seq_num_hosts)
    assert gateway == server._gateway_address
    assert LEASE_DURATION == server._lease_duration
    assert DHCP_CLIENT_PORT == server._dhcp_client_port
    assert RESERVATION_TIME == server._reservation_time
    assert 1 == next(server._size_packet_dhcp)


def feed_on_packet(payload,
                   server=default_server(),
                   mock_thread=patch("itsim.machine.process_management.thread.Thread").start(),
                   mock_pack=patch("itsim.network.packet.Packet").start(),
                   mock_sock=patch("itsim.machine.socket.Socket").start(),
                   sim_time=1):
    mock_pack.payload = payload
    flag = 0

    def run():
        nonlocal flag
        flag = 1
        server.on_packet(mock_thread, mock_pack, mock_sock)

    sim = Simulator()
    sim.add(run)
    sim.run(sim_time)
    assert 1 == flag


def test_on_packet_drop(server):
    server._handle_discover = Mock()
    server._handle_request = Mock()

    feed_on_packet({}, server)
    feed_on_packet({Field.NODE_ID: 0}, server)
    feed_on_packet({Field.MESSAGE: 0}, server)
    feed_on_packet({Field.MESSAGE: 0, Field.NODE_ID: 0}, server)

    server._handle_discover.assert_not_called()
    server._handle_request.assert_not_called()


@patch("itsim.machine.socket.Socket")
def test_discover_relaxed(mock_sock, server):
    node_id = uuid4()
    address = as_address("192.168.1.2")

    mock_sock.send = Mock()
    feed_on_packet({Field.MESSAGE: DHCP.DISCOVER, Field.NODE_ID: node_id},
                   server=server,
                   mock_sock=mock_sock)
    mock_sock.send.assert_called_once_with((server._cidr.broadcast_address, server._dhcp_client_port),
                                           1,
                                           {Field.MESSAGE: DHCP.OFFER,
                                            Field.ADDRESS: address,
                                            Field.SERVER: server._gateway_address,
                                            Field.NODE_ID: node_id})

    assert node_id in server._address_allocation
    assert not server._address_allocation[node_id].is_confirmed
    assert address == server._address_allocation[node_id].address
    assert server._reserved[address]


@patch("itsim.machine.socket.Socket")
def test_discover_request(mock_sock, server):
    node_id = uuid4()
    request = as_address("192.168.1.4")

    mock_sock.send = Mock()
    feed_on_packet({Field.MESSAGE: DHCP.DISCOVER,
                    Field.NODE_ID: node_id,
                    Field.ADDRESS: request},
                   server,
                   mock_sock=mock_sock)

    mock_sock.send.assert_called_once_with((server._cidr.broadcast_address, server._dhcp_client_port),
                                           1,
                                           {Field.MESSAGE: DHCP.OFFER,
                                            Field.ADDRESS: request,
                                            Field.SERVER: server._gateway_address,
                                            Field.NODE_ID: node_id})

    assert node_id in server._address_allocation
    assert not server._address_allocation[node_id].is_confirmed
    assert request == server._address_allocation[node_id].address
    assert server._reserved[request]


@patch("itsim.machine.socket.Socket")
def test_expiry(mock_sock, server):
    node_id = uuid4()
    request = as_address("192.168.1.4")

    mock_sock.send = Mock()
    feed_on_packet({Field.MESSAGE: DHCP.DISCOVER,
                    Field.NODE_ID: node_id,
                    Field.ADDRESS: request},
                   server,
                   mock_sock=mock_sock,
                   sim_time=server._reservation_time + 1)

    mock_sock.send.assert_called_once_with((server._cidr.broadcast_address, server._dhcp_client_port),
                                           1,
                                           {Field.MESSAGE: DHCP.OFFER,
                                            Field.ADDRESS: request,
                                            Field.SERVER: server._gateway_address,
                                            Field.NODE_ID: node_id})

    assert node_id not in server._address_allocation
    assert request not in server._reserved


def test_decline():
    server = DHCPServer(1,
                        as_cidr("192.168.1.0/30"),
                        as_address("192.168.1.1"),
                        size_packet_dhcp=constant(1))
    for i in range(server._num_hosts_max + 1):
        with patch("itsim.machine.socket.Socket") as mock_sock:
            mock_sock.send = Mock()
            feed_on_packet({Field.MESSAGE: DHCP.DISCOVER, Field.NODE_ID: uuid4()},
                           server=server,
                           mock_sock=mock_sock)
            if i < server._num_hosts_max:
                print()
                mock_sock.send.assert_called_once()
            else:
                mock_sock.send.assert_not_called()
