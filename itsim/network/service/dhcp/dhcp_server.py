from itertools import cycle
from typing import Any, cast, Mapping, MutableMapping, Optional
from uuid import UUID, uuid4

from greensim.random import normal, VarRandom

from .__init__ import DHCP, DHCP_CLIENT_PORT, DHCP_HEADER_SIZE, DHCP_SIZE_MEAN, DHCP_SIZE_STDEV, Field, \
    LEASE_DURATION, RESERVATION_TIME

from itsim.network.packet import Packet
from itsim.machine.process_management import _Thread
from itsim.machine.process_management.daemon import Daemon
from itsim.machine.socket import Socket
from itsim.random import num_bytes
from itsim.simulator import advance
from itsim.types import Address, as_address, Cidr, Payload


# Represents a reservation of a particular address in a DHCPServer
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
        self._reserved: MutableMapping[Address, bool] = {}
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
                if suggestion not in self._reserved:
                    break
            else:
                # Decline to allocate as per https://tools.ietf.org/html/rfc2131#section-4.3.1
                return

        self._address_allocation[node_id] = _AddressAllocation(suggestion)
        self._reserved[suggestion] = True
        socket.sendto(
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
            del self._reserved[self._address_allocation[node_id].address]
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
            socket.sendto(
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
