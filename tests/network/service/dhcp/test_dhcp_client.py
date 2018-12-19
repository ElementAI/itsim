from greensim.random import constant

from itsim.machine.socket import Timeout
from itsim.network.location import Location
from itsim.network.packet import Packet
# These tests will actually fail if __init__ is dropped since the Field Enum in
# this file no longer meets the == condition with the one in DHCPClient
# This is a quirk of Python imports that warrants investigation
from itsim.network.service.dhcp.__init__ import DHCP, DHCP_CLIENT_PORT, DHCP_CLIENT_RETRIES, DHCP_SERVER_PORT, Field, \
    RESERVATION_TIME
from itsim.network.service.dhcp.client import DHCPClient
from itsim.simulator import advance, Simulator
from itsim.types import as_address, as_cidr

from pytest import fail, fixture, raises

from unittest.mock import call, Mock, patch

from uuid import uuid4


@fixture
def client():
    return default_client()


# Pytest throws an error if you try to call a fixture directly
@patch("itsim.network.interface.Interface")
def default_client(mock_face):
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


# Test the case where _dhcp_discover returns None
@patch("itsim.machine.process_management.thread.Thread")
def test_get_none_address(mock_thread, client):
    client._dhcp_discover = Mock(return_value=None)
    client._dhcp_request = Mock()

    assert not client._dhcp_get_address(mock_thread)

    client._dhcp_discover.assert_called_once()
    client._dhcp_request.assert_not_called()


# Test the case where _dhcp_discover times out
@patch("itsim.machine.process_management.thread.Thread")
def test_get_address_timeout(mock_thread, client):
    client._dhcp_discover = Mock(side_effect=Timeout())
    client._dhcp_request = Mock()

    assert not client._dhcp_get_address(mock_thread)

    client._dhcp_discover.assert_called_once()
    client._dhcp_request.assert_not_called()


# Test the case where _dhcp_discover returns something valid
@patch("itsim.machine.process_management.thread.Thread")
def test_get_address_returned(mock_thread, client):
    client._dhcp_discover = Mock(return_value=as_address("0.0.0.0"))
    client._dhcp_request = Mock(return_value=True)

    assert client._dhcp_get_address(mock_thread)

    client._dhcp_discover.assert_called_once()
    client._dhcp_request.assert_called_once()


# This handles the complications of delivering streams of packets to _dhcp_iter_responses() through recv()
# It is generalized to be useful for any function that relies on recv() by deferring all assertion logic to f_run
def run_packets(received_payloads,
                f_run,  # A function that handles calling the right method on DHCPClient and making assertions
                sim_time=RESERVATION_TIME + 1,
                set_dest=None):

    with patch("itsim.machine.socket.Socket") as mock_sock, patch("itsim.network.location.Location") as mock_loc:

        # Testing _dhcp_request requires that the Packet destination is valid, but does not care about the source
        if set_dest is not None:
            dest = Location(set_dest, 0)
        else:
            dest = mock_loc

        received_packets = [Packet(mock_loc, dest, 0, p) for p in received_payloads]

        # It's possible to do this by just setting `mock_sock.recv = Mock(side_effect=received_packets)`
        # but the Iterator throws StopIteration at the end of the list, which triggers a Pytest DeprecationWarning
        # which, in turn, requires an unusual filter https://docs.python.org/3.5/library/warnings.html#warning-filter
        # Using the Generator pattern to avoid setting up a whole new class also does not work since recv() is
        # not implemented to use the pattern, so the received packet variable is not set correctly
        class CleanRelease:
            i = 0

            def next(self, *args):
                if self.i < len(received_packets):
                    self.i += 1
                    # Force the passage of time so that test_recv_time_expired can test the reservation expiration
                    advance(1)
                    return received_packets[self.i - 1]
                # This is what recv() eventually does, which leads to the termination of _dhcp_iter_responses()
                raise Timeout()

        # Each time recv is called, a new packet will be pulled from the list. When it's empty Timeout will be raised
        mock_sock.recv = Mock(side_effect=CleanRelease().next)

        # Flags that the simulation function under test (run()) ran to completion by setting flag = 1
        flag = 0

        def run():
            nonlocal flag

            f_run(mock_sock)

            flag = 1

        sim = Simulator()
        sim.add(run)
        sim.run(sim_time)

        assert 1 == flag
        # Count the number of times recv was called
        recv_count = len(mock_sock.recv.mock_calls)
        # Assert all the recv calls occured at the correct time, based on the 1 second delay
        mock_sock.recv.assert_has_calls([call(RESERVATION_TIME - t) for t in range(recv_count)])
        return recv_count


# This is generalized for the varying corner cases of _dhcp_iter_responses via on_pack and on_no_pack
# on_pack is called with a packet and its index every time it passes the _dhcp_iter_responses checks
# on_no_pack is called if Timeout is raised by recv() and no packets have passed the checks
def run_packets_iter(received_payloads,
                     on_pack,  # Populate this with assertions and other checks for the incoming packets
                     on_no_pack,  # Populate this with logic about how to handle a lack of packets
                     client=default_client(),
                     node_id=uuid4(),
                     msg=DHCP.OFFER):
    packs_in = 0

    def f_run(mock_sock):
        nonlocal packs_in

        for pack in client._dhcp_iter_responses(mock_sock, node_id, msg):
            on_pack(pack, packs_in)
            packs_in += 1

        if packs_in == 0:
            on_no_pack()

        return packs_in

    calls = run_packets(received_payloads, f_run)
    # recv should be called at least as many times as packets were recieved
    assert calls >= packs_in
    # Return the number of packets processed (the last recv times out)
    # This needs to be here and not in run_packets to handle the corner case where time_remaining = 0.0
    # And recv is not called a final time
    return calls - 1


# This depends on run_packets to feed in packets that will be processed by _dhcp_discover
# It is also possible to do this by mocking _dhcp_iter_responses, but that requires duplicatiing
# much of the logic in run_packets
def run_packets_discover(received_payloads, node_id):

    with patch("itsim.network.interface.Interface") as mock_face:
        mock_face.cidr = as_cidr("10.10.128.0/17")
        client = DHCPClient(mock_face, size_packet_dhcp=constant(1))
        out = None

        def f_run(mock_sock):
            nonlocal out
            out = client._dhcp_discover(mock_sock, node_id)
            # Assert the server was called with the correct inputs
            mock_sock.send.assert_called_once_with(
                (client._interface.cidr.broadcast_address, client._dhcp_server_port),
                1,
                {Field.MESSAGE: DHCP.DISCOVER, Field.NODE_ID: node_id})

        run_packets(received_payloads, f_run)
        return out


# This depends on run_packets to feed in packets that will be processed by _dhcp_request
# It is also possible to do this by mocking _dhcp_iter_responses, but that requires duplicatiing
# much of the logic in run_packets
def run_packets_request(received_payloads,
                        addr_orig=as_address("0.0.0.0"),
                        addr=as_address("10.10.128.1"),
                        pack_dest=as_address("10.10.128.1"),
                        node_id=uuid4()):

    with patch("itsim.network.interface.Interface") as mock_face:
        mock_face.cidr = as_cidr("10.10.128.0/17")
        mock_face.address = addr_orig
        client = DHCPClient(mock_face, size_packet_dhcp=constant(1))
        success = None

        def f_run(mock_sock):
            nonlocal success
            success = client._dhcp_request(mock_sock, node_id, addr)
            # Assert the server was called with the correct inputs
            mock_sock.send.assert_called_once_with(
                (client._interface.cidr.broadcast_address, client._dhcp_server_port),
                1,
                {Field.MESSAGE: DHCP.REQUEST,
                 Field.NODE_ID: node_id,
                 Field.ADDRESS: addr})
            # Assert that the address has been set correctly after resolution
            if success:
                assert client._interface.address == addr
            else:
                assert client._interface.address == addr_orig

        run_packets(received_payloads, f_run, set_dest=pack_dest)
        return success


def test_socket_recv_valid():
    node_id = uuid4()
    msg = DHCP.OFFER
    payload = {Field.MESSAGE: msg, Field.NODE_ID: node_id}

    def check_packet(p, n):
        assert payload == p.payload

    assert 1 == run_packets_iter([payload],
                                 check_packet,
                                 fail,  # Fail on no packets received
                                 node_id=node_id,
                                 msg=msg)


def test_socket_recv_valid_ordered():
    node_id = uuid4()
    msg = DHCP.OFFER
    # This test is valid for any number of packets greater than 1. The choice of 10 is arbitrary
    n_packs = 10
    payloads = [{Field.MESSAGE: msg, Field.NODE_ID: node_id, "key": uuid4()} for i in range(n_packs)]

    def check_packet(p, n):
        assert payloads[n] == p.payload

    assert n_packs == run_packets_iter(payloads,
                                       check_packet,
                                       fail,  # Fail on no packets received
                                       node_id=node_id,
                                       msg=msg)


def test_recv_time_expired():
    node_id = uuid4()
    msg = DHCP.OFFER
    payloads = [{Field.MESSAGE: msg, Field.NODE_ID: node_id, "key": uuid4()} for i in range(int(RESERVATION_TIME))]

    def check_packet(p, n):
        assert payloads[n] == p.payload

    # The last packet shouldn't have be received since time advances 1 second per packet and expires at RESERVATION_TIME
    assert RESERVATION_TIME - 1 == run_packets_iter(payloads,
                                                    check_packet,
                                                    fail,  # Fail on no packets received
                                                    node_id=node_id,
                                                    msg=msg)


def test_socket_timeout(client):
    no_pack_flag = 0

    # Strictly speaking this is not necessary when on_pack is fail since run_packets either calls one or
    # the other, so a lack of failure is equivalent to success. This just makes the test more robust
    def no_pack():
        nonlocal no_pack_flag
        no_pack_flag = 1

    # Assert that no packets were received and confirm that no_pack was called, as expected
    assert 0 == run_packets_iter([], fail, no_pack)
    assert 1 == no_pack_flag


def test_invalid_packets(client):
    node_id = uuid4()
    msg = DHCP.OFFER
    packs = [
        {},
        # Right message, wrong ID
        {Field.MESSAGE: msg, Field.NODE_ID: uuid4()},
        {Field.MESSAGE: msg},
        # Right ID, wrong message
        {Field.MESSAGE: DHCP.DISCOVER, Field.NODE_ID: node_id},
        {Field.NODE_ID: node_id}
    ]

    assert len(packs) == run_packets_iter(packs,
                                          fail,  # Fail on packet receipt
                                          lambda: 0,  # Pass on the zero packet case
                                          node_id=node_id,
                                          msg=msg)


def test_discover_valid():
    node_id = uuid4()
    addr = as_address("10.10.128.1")
    pay = {Field.MESSAGE: DHCP.OFFER, Field.NODE_ID: node_id, Field.ADDRESS: addr}
    assert addr == run_packets_discover([pay], node_id)


def test_discover_invalid():
    node_id = uuid4()
    pay = {Field.MESSAGE: DHCP.OFFER, Field.NODE_ID: node_id}
    assert run_packets_discover([pay], node_id) is None


def test_request_valid():
    node_id = uuid4()
    addr_orig = as_address("0.0.0.0"),
    addr = as_address("10.10.128.1")
    pay = {Field.MESSAGE: DHCP.ACK, Field.NODE_ID: node_id, Field.ADDRESS: addr}
    assert run_packets_request([pay], addr_orig, addr, addr, node_id)


def test_request_wrong_return_location():
    node_id = uuid4()
    addr_orig = as_address("0.0.0.0"),
    addr = as_address("10.10.128.1")
    other = as_address("10.10.128.2")
    pay = {Field.MESSAGE: DHCP.ACK, Field.NODE_ID: node_id, Field.ADDRESS: addr}
    assert not run_packets_request([pay], addr_orig, addr, other, node_id)


def test_request_invalid_return_packet():
    addr_orig = as_address("0.0.0.0"),
    addr = as_address("10.10.128.1")
    # Random ID
    pay = {Field.MESSAGE: DHCP.ACK, Field.NODE_ID: uuid4(), Field.ADDRESS: addr}
    assert not run_packets_request([pay], addr_orig, addr, addr, uuid4())


# The contract between the client and server requires that the client is able to receive its ACK on the newly
# allocated address, so this checks that when it goes into the waiting loop for packets that address is set correctly
@patch("itsim.machine.socket.Socket")
def test_temp_interface_set(mock_sock, client):
    addr = as_address("10.10.128.1")
    client._interface.address = as_address("0.0.0.0"),

    class AdHocException(Exception):
        pass

    def assert_and_raise(*args):
        assert addr == client._interface.address
        # Raising here conveniently proves the function ran and halts it, which removes the need to do more mocking
        raise AdHocException()

    client._dhcp_iter_responses = Mock(side_effect=assert_and_raise)

    with raises(AdHocException):
        client._dhcp_request(mock_sock, uuid4(), addr)
