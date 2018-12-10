from enum import Enum, unique
from itertools import cycle
from typing import Any, cast, Generator, Mapping, MutableMapping, Optional
from uuid import UUID, uuid4

from greensim.random import normal, VarRandom

from itsim.network.interface import Interface
from itsim.network.packet import Packet
from itsim.machine.process_management import _Thread
from itsim.machine.process_management.daemon import Daemon
from itsim.machine.process_management.thread import Thread
from itsim.machine.socket import Socket, Timeout
from itsim.random import num_bytes
from itsim.simulator import now, advance
from itsim.types import Address, as_address, Cidr, Payload, Protocol
from itsim.units import B, S


LEASE_DURATION = 86400 * S
DHCP_SERVER_PORT = 67
DHCP_CLIENT_PORT = 68
DHCP_CLIENT_RETRIES = 3
DHCP_SIZE_MEAN = 100.0 * B
DHCP_SIZE_STDEV = 30.0 * B
DHCP_HEADER_SIZE = 240 * B
RESERVATION_TIME = 30 * S


@unique
class DHCP(Enum):
    DISCOVER = "DHCPDISCOVER"
    OFFER = "DHCPOFFER"
    REQUEST = "DHCPREQUEST"
    ACK = "DHCPACK"


@unique
class Field(Enum):
    MESSAGE = "message"
    NODE_ID = "node_id"
    ADDRESS = "address"
    LEASE_DURATION = "lease"
    SERVER = "server"


# Represents a reservation of a particular address in a DHCPDaemon
class _AddressAllocation:

    def __init__(self, address: Address) -> None:
        self._address = address
        self._unique = uuid4()
        self._is_confirmed = False

    @property
    def address(self) -> Address:
        return self._address

    @property
    def unique(self) -> UUID:
        return self._unique

    @property
    def is_confirmed(self) -> bool:
        return self._is_confirmed

    @is_confirmed.setter
    def is_confirmed(self, is_confirmed: bool) -> None:
        self._is_confirmed = is_confirmed

    def __repr__(self) -> str:
        return f"AA[{self.address}, {str(self.unique)[0:3]}, {self.is_confirmed}]"


class DHCPServer(Daemon):
    """
    Initialize a :py:class:`DHCPDaemon`, which is a :py:class:`~itsim.machine.process_management.daemon.Daemon` for
    handling the server side of the DHCP interaction

    :param cidr:
        The CIDR for which this instance is expected to allocate addresses
    :param gateway_address:
        Gateway to the Internet for this network
    :param lease_duration:
        Duration of address leases issued by this instance. Defaults to one day
    :param dhcp_client_port:
        Port used by DHCP clients on this network. Defaults to 68
    :param reservation_time:
        Maximum delay between the allocation of an address by this instance and the confirmation from the client.
        Defaults to 30 seconds
    :param size_packet_dhcp:
        A `greensim.random.VarRandom[int]` which will be sampled to produce the sizes of packets sent by this server
    """

    def __init__(self, num_host_first: int,
                 cidr: Cidr,
                 gateway_address: Address,
                 lease_duration: float = LEASE_DURATION,
                 dhcp_client_port: int = DHCP_CLIENT_PORT,
                 reservation_time: float = RESERVATION_TIME,
                 size_packet_dhcp: VarRandom[int] = num_bytes(
                     normal(DHCP_SIZE_MEAN, DHCP_SIZE_STDEV), header = DHCP_HEADER_SIZE
                 )) -> None:

        super().__init__(self.on_packet)
        if num_host_first <= 0:
            raise ValueError(f"num_host first >= 1 (here {num_host_first})")
        self._address_allocation: MutableMapping[UUID, _AddressAllocation] = {}
        self._cidr = cidr
        upper_num_host = int(self._cidr.hostmask)
        if num_host_first >= upper_num_host:
            raise ValueError(
                f"First host number is too high ({num_host_first}) for this link's CIDR; use " +  # noqa: W504
                f"{upper_num_host - 1} or lower."
            )
        self._num_hosts_max = upper_num_host - num_host_first
        self._seq_num_hosts = cycle(as_address(n, self._cidr) for n in range(num_host_first, upper_num_host))
        self._gateway_address = gateway_address
        self._lease_duration = lease_duration
        self._dhcp_client_port = dhcp_client_port
        self._reservation_time = reservation_time
        self._size_packet_dhcp = size_packet_dhcp

    def on_packet(self, thread: _Thread, packet: Packet, socket: Socket) -> None:
        """
        General-purpose method for handling all :py:class:`~itsim.network.packet.Packet` objects received.
        This is expected to be called as result of the call to
        :py:meth:`~itsim.machine.process_management.daemon.Daemon.trigger`
        made by :py:meth:`~itsim.machine.Node.run_networking_daemon`

        NB In the DHCP process all packets except ACK are sent to the broadcast address

        :param thread:
            The :py:class:`~itsim.machine.process_management.thread.Thread` that this method is executing in
        :param packet:
            The :py:class:`~itsim.network.packet.Packet` that was received
        :param socket:
            The :py:class:`~itsim.machine.socket.Socket` to be used for sending any
            :py:class:`~itsim.network.packet.Packet` necessary in response
        """
        payload = cast(Mapping[Field, Any], packet.payload)
        if Field.MESSAGE not in payload or Field.NODE_ID not in payload:
            # Don't bother processing ill-formed messages.
            return

        message = payload[Field.MESSAGE]
        node_id = payload[Field.NODE_ID]

        address_maybe = None
        if Field.ADDRESS in payload:
            address_maybe = as_address(payload[Field.ADDRESS], self._cidr)

        if message == DHCP.DISCOVER:
            self._handle_discover(socket, node_id, address_maybe)
        elif message == DHCP.REQUEST and address_maybe is not None:
            self._handle_request(socket, node_id, address_maybe)
        else:
            # Can't do anything with this, drop.
            return

    def _handle_discover(self, socket: Socket, node_id: UUID, address_maybe: Optional[Address]) -> None:
        """
        Respond to the Discover step of DHCP by allocating and broadcasting an :py:class:`~itsim.types.Address`

        :param socket:
            The :py:class:`~itsim.machine.socket.Socket` to be used for broadcasting the new allocation
        :param node_id:
            UUID unique to the :py:class:`~itsim.machine.Node` requesting an allocation.
            In practice, this is a stand-in for a MAC address
        :param address_maybe:
            If the client requested a specific :py:class:`~itsim.types.Address`, it should be passed in here
        """
        if address_maybe is not None and address_maybe not in self._address_allocation:
            suggestion = cast(Address, address_maybe)
        else:
            for _ in range(self._num_hosts_max):
                suggestion = next(self._seq_num_hosts)
                if suggestion not in self._address_allocation:
                    break
            else:
                # Decline to allocate as per https://tools.ietf.org/html/rfc2131#section-4.3.1
                return

        self._address_allocation[node_id] = _AddressAllocation(suggestion)
        socket.send(
            (self._cidr.broadcast_address, self._dhcp_client_port),
            next(self._size_packet_dhcp),
            cast(Payload, {
                Field.MESSAGE: DHCP.OFFER,
                Field.ADDRESS: suggestion,
                Field.SERVER: self._gateway_address,
                Field.NODE_ID: node_id
            })
        )

        # Reserve for 30 seconds -- a REQUEST for the address must have been received by then.
        # Otherwise, drop the reservation.
        unique = self._address_allocation[node_id].unique
        advance(self._reservation_time)
        if not self._address_allocation[node_id].is_confirmed and self._address_allocation[node_id].unique == unique:
            del self._address_allocation[node_id]

    def _handle_request(self, socket: Socket, node_id: UUID, address: Address) -> None:
        """
        Respond to the Requesting step of DHCP by allocating and ACKing an :py:class:`~itsim.types.Address`

        :param socket:
            The :py:class:`~itsim.machine.socket.Socket` to be used for sending the ACK
        :param node_id:
            UUID unique to the :py:class:`~itsim.machine.Node` requesting an allocation.
            In practice, this is a stand-in for a MAC address
        :param address:
            The :py:class:`~itsim.types.Address` being confirmed.
        """

        if node_id in self._address_allocation and address == self._address_allocation[node_id].address:
            # This REQUEST is proper, confirming the allocation of the address.
            self._address_allocation[node_id].is_confirmed = True
            socket.send(
                (address, self._dhcp_client_port),
                next(self._size_packet_dhcp),
                cast(Payload, {
                    Field.MESSAGE: DHCP.ACK,
                    Field.ADDRESS: address,
                    Field.NODE_ID: node_id,
                    Field.LEASE_DURATION: self._lease_duration
                })
            )
        else:
            # Spurious REQUEST! Drop.
            return


class DHCPClient(Daemon):
    """
    Initialize a :py:class:`DHCPClient`, which is a :py:class:`~itsim.machine.process_management.daemon.Daemon` for
    handling the client side of the DHCP interaction

    :param interface:
        The :py:class:`~itsim.network.interface.Interface` that this client should seek an
        :py:class:`~itsim.types.Address` for
    :param dhcp_server_port:
        Port used by DHCP servers on this network. Defaults to 67
    :param dhcp_client_port:
        Port used by DHCP clients on this network. Defaults to 68
    :param dhcp_client_retries:
        Number of times to attempt requesting an address before giving up. Defaults to 3
    :param reservation_time:
        Maximum delay between the allocation of an address by this instance and the confirmation from the client.
        Defaults to 30 seconds
    :param size_packet_dhcp:
        A `greensim.random.VarRandom[int]` which will be sampled to produce the sizes of packets sent by this client
    """

    def __init__(self,
                 interface: Interface,
                 dhcp_server_port: int = DHCP_SERVER_PORT,
                 dhcp_client_port: int = DHCP_CLIENT_PORT,
                 dhcp_client_retries: int = DHCP_CLIENT_RETRIES,
                 reservation_time: float = RESERVATION_TIME,
                 size_packet_dhcp: VarRandom[int] = num_bytes(
                     normal(DHCP_SIZE_MEAN, DHCP_SIZE_STDEV), header = DHCP_HEADER_SIZE
                 )) -> None:
        super().__init__(self.run_client)
        self._interface = interface
        self._dhcp_server_port = dhcp_server_port
        self._dhcp_client_port = dhcp_client_port
        self._dhcp_client_retries = dhcp_client_retries
        self._reservation_time = reservation_time
        self._size_packet_dhcp = size_packet_dhcp

    def run_client(self, thread: Thread) -> None:
        """
        Attempt and, if necessary retry, to resolve an :py:class:`~itsim.types.Address` for the
        :py:class:`~itsim.network.interface.Interface` that this client is assigned to

        This is expected to be called as result of the call to
        :py:meth:`~itsim.machine.process_management.daemon.Daemon.trigger`
        made by :py:meth:`~itsim.machine.Node.run_networking_daemon`

        :param thread:
            The :py:class:`~itsim.machine.process_management.thread.Thread` that this method is executing in
        """
        for _ in range(self._dhcp_client_retries):
            # Retry after each failure to get an address.
            if self._dhcp_get_address(thread):
                break

    def _dhcp_iter_responses(self, socket: Socket, node_id: UUID, message: DHCP) -> Generator[Packet, None, None]:
        """
        Filter incoming :py:class:`~itsim.network.packet.Packet` objects until one is found for this client
        or the reservation time expires, whichever comes first

        :param socket:
            The :py:class:`~itsim.machine.socket.Socket` to be used for broadcasting the new allocation
        :param node_id:
            UUID unique to the :py:class:`~itsim.machine.Node` requesting an allocation via this client.
            In practice, this is a stand-in for a MAC address
        :param message:
            The type of message to wait on (e.g., offer)
        """
        time_remaining = self._reservation_time
        while time_remaining >= 0.0:
            try:
                time_before_recv = now()
                packet = socket.recv(time_remaining)
                time_remaining -= (now() - time_before_recv)
                if packet.payload.get(cast(str, Field.MESSAGE)) == message and \
                   packet.payload.get(cast(str, Field.NODE_ID)) == node_id:
                    yield packet
            except Timeout:
                return

    def _dhcp_discover(self, socket: Socket, node_id: UUID) -> Optional[Address]:
        """
        Begin the Discover step of DHCP by requesting an :py:class:`~itsim.types.Address`

        :param socket:
            The :py:class:`~itsim.machine.socket.Socket` to be used for broadcasting the new allocation
        :param node_id:
            UUID unique to the :py:class:`~itsim.machine.Node` requesting an allocation.
            In practice, this is a stand-in for a MAC address
        """

        socket.send(
            (self._interface.cidr.broadcast_address, self._dhcp_server_port),
            next(self._size_packet_dhcp),
            cast(Payload, {Field.MESSAGE: DHCP.DISCOVER, Field.NODE_ID: node_id})
        )

        # Wait for our OFFER.
        for packet in self._dhcp_iter_responses(socket, node_id, DHCP.OFFER):
            if Field.ADDRESS in packet.payload:
                return cast(Address, packet.payload[cast(str, Field.ADDRESS)])

        return None

    def _dhcp_request(self, socket: Socket, node_id: UUID, address_proposed: Address) -> bool:
        """
        Begin the request step of DHCP by saving and confirming an :py:class:`~itsim.types.Address`

        :param socket:
            The :py:class:`~itsim.machine.socket.Socket` to be used for broadcasting the new allocation
        :param node_id:
            UUID unique to the :py:class:`~itsim.machine.Node` requesting an allocation.
            In practice, this is a stand-in for a MAC address
        :param address_proposed:
            The :py:class:`~itsim.types.Address` that was offered and should be confirmed
        """

        socket.send(
            (self._interface.cidr.broadcast_address, self._dhcp_server_port),
            next(self._size_packet_dhcp),
            cast(Payload, {Field.MESSAGE: DHCP.REQUEST, Field.NODE_ID: node_id, Field.ADDRESS: address_proposed})
        )

        # Set the interface to the new address, in the expecation it will be confirmed
        address_orig = self._interface.address
        # NB this affects the action of socket.recv(), so it must come before that call
        self._interface.address = cast(Address, address_proposed)
        # Wait for our ACK.
        for packet in self._dhcp_iter_responses(socket, node_id, DHCP.ACK):
            if packet.dest.hostname_as_address() == address_proposed:
                return True
        # The address was not confirmed, fall back
        self._interface.address = address_orig
        return False

    def _dhcp_get_address(self, thread: Thread) -> bool:
        """
        Make a single attempt to resolve an :py:class:`~itsim.types.Address` for the
        :py:class:`~itsim.network.interface.Interface` that this client is assigned to

        :param thread:
            The :py:class:`~itsim.machine.process_management.thread.Thread` that this method is executing in
        """
        node_id = thread.process.node.uuid
        try:
            with thread.process.node.bind(Protocol.UDP, self._dhcp_client_port, thread.process.pid) as socket:
                address = self._dhcp_discover(socket, node_id)
                if address is not None:
                    return self._dhcp_request(socket, node_id, address)

        except Timeout:
            pass

        return False
