from greensim.random import constant

from itsim.machine.socket import Timeout
# These tests will actually fail if __init__ is dropped since the Field Enum in
# this file no longer meets the == condition with the one in DHCPClient
# This is a quirk of Python imports that warrants investigation
from itsim.network.service.dhcp.__init__ import DHCP, DHCP_CLIENT_PORT, DHCP_CLIENT_RETRIES, DHCP_SERVER_PORT,\
    RESERVATION_TIME
from itsim.network.service.dhcp.dhcp_client import DHCPClient
from itsim.simulator import advance, Simulator

from pytest import fixture

from unittest.mock import Mock, patch

from uuid import uuid4


@fixture
@patch("itsim.network.interface.Interface")
def client(mock_face):
    return DHCPClient(mock_face, size_packet_dhcp=constant(1))


@patch("itsim.network.interface.Interface")
def test_init(mock_face):
    client = DHCPClient(mock_face, size_packet_dhcp=constant(1))
    assert mock_face == client._interface
    assert DHCP_SERVER_PORT == client._dhcp_server_port
    assert DHCP_CLIENT_PORT == client._dhcp_client_port
    assert DHCP_CLIENT_RETRIES == client._dhcp_client_retries
    assert RESERVATION_TIME == client._reservation_time
    assert 1 == next(client._size_packet_dhcp)


@patch("itsim.machine.process_management.thread.Thread")
def test_none_address(mock_thread, client):
    client._dhcp_discover = Mock(return_value=None)
    client._dhcp_request = Mock()

    assert not client._dhcp_get_address(mock_thread)

    client._dhcp_discover.assert_called_once()
    client._dhcp_request.assert_not_called()


@patch("itsim.machine.process_management.thread.Thread")
def test_address_timeout(mock_thread, client):
    client._dhcp_discover = Mock(side_effect=Timeout())
    client._dhcp_request = Mock()

    assert not client._dhcp_get_address(mock_thread)

    client._dhcp_discover.assert_called_once()
    client._dhcp_request.assert_not_called()


@patch("itsim.machine.socket.Socket")
@patch("itsim.network.packet.Packet")
def test_socket_recv(mock_sock, mock_pack, client):
    # Return a mock Packet and delay 1 second
    mock_sock.recv = Mock(return_value=mock_pack, side_effect=lambda *args: advance(1))

    def run():
        for pack in client._dhcp_iter_responses(mock_sock, uuid4(), DHCP.OFFER):
            assert mock_pack == pack

    sim = Simulator()
    sim.add(run)
    sim.run(1)
