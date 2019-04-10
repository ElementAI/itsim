from typing import cast, Generator, Optional
from uuid import UUID

from greensim.random import normal, VarRandom

from .__init__ import DHCP, DHCP_CLIENT_PORT, DHCP_CLIENT_RETRIES, DHCP_HEADER_SIZE, DHCP_SERVER_PORT, DHCP_SIZE_MEAN, \
    DHCP_SIZE_STDEV, Field, RESERVATION_TIME


from itsim.network.interface import Interface
from itsim.network.packet import Packet
from itsim.machine.process_management.daemon import Daemon
from itsim.machine.socket import Socket, Timeout
from itsim.random import num_bytes
from itsim.simulator import now
from itsim.software.context import Context
from itsim.types import Address, Payload, Protocol


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
                     normal(DHCP_SIZE_MEAN, DHCP_SIZE_STDEV), header=DHCP_HEADER_SIZE
                 )) -> None:
        super().__init__(self.run_client)
        self._interface = interface
        self._dhcp_server_port = dhcp_server_port
        self._dhcp_client_port = dhcp_client_port
        self._dhcp_client_retries = dhcp_client_retries
        self._reservation_time = reservation_time
        self._size_packet_dhcp = size_packet_dhcp

    def run_client(self, context: Context) -> None:
        """
        Attempt and, if necessary retry, to resolve an :py:class:`~itsim.types.Address` for the
        :py:class:`~itsim.network.interface.Interface` that this client is assigned to

        This is expected to be called as result of the call to
        :py:meth:`~itsim.machine.process_management.daemon.Daemon.trigger`
        made by :py:meth:`~itsim.machine.Node.run_networking_daemon`

        :param context:
            :py:class:`~itsim.software.Context` for running this computation.
        """
        for _ in range(self._dhcp_client_retries):
            # Retry after each failure to get an address.
            if self._dhcp_get_address(context):
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
        while time_remaining > 0.0:
            try:
                time_before_recv = now()
                packet = socket.recv(time_remaining)
            except Timeout:
                return

            time_remaining -= (now() - time_before_recv)
            if packet.payload.get(cast(str, Field.MESSAGE)) == message and \
               packet.payload.get(cast(str, Field.NODE_ID)) == node_id:
                yield packet

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

        address_orig = self._interface.address
        # Set the interface to the new address, in the expectation it will be confirmed
        # NB this affects the action of socket.recv(), so it must come before that call
        self._interface.address = cast(Address, address_proposed)
        # Wait for our ACK.
        for packet in self._dhcp_iter_responses(socket, node_id, DHCP.ACK):
            if packet.dest.hostname_as_address() == address_proposed:
                return True
        # The address was not confirmed, fall back
        self._interface.address = address_orig
        return False

    def _dhcp_get_address(self, context: Context) -> bool:
        """
        Make a single attempt to resolve an :py:class:`~itsim.types.Address` for the
        :py:class:`~itsim.network.interface.Interface` that this client is assigned to

        :param context:
            Computation :py:class:`~itsim.software.Context`.
        """
        node_id = context.process.node.uuid
        try:
            with context.node.bind(Protocol.UDP, self._dhcp_client_port, context.process.pid) as socket:
                address = self._dhcp_discover(socket, node_id)
                if address is not None:
                    return self._dhcp_request(socket, node_id, address)

        except Timeout:
            pass

        return False
