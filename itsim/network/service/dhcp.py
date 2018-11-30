from enum import Enum, unique
from itertools import cycle
from typing import Any, cast, Generator, Mapping, MutableMapping, Optional
from uuid import UUID, uuid4

from greensim.random import normal

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


LEN_PACKET_DHCP = 348
LEASE_DURATION = 86400
DHCP_SERVER_PORT = 67
DHCP_CLIENT_PORT = 68
DHCP_CLIENT_RETRIES = 3
RESERVATION_TIME_SECONDS = 30


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


class DHCPDaemon(Daemon):
    responses = {"DHCPDISCOVER": "DHCPOFFER", "DHCPREQUEST": "DHCPACK"}
    size_packet_dhcp = num_bytes(normal(100.0 * B, 30.0 * B), header=240 * B)

    def __init__(self, num_host_first: int, cidr: Cidr, address: Address) -> None:
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
        self._address_mine = address

    def on_packet(self, thread: _Thread, packet: Packet, socket: Socket) -> None:
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
            self.handle_discover(socket, node_id, address_maybe)
        elif message == DHCP.REQUEST:
            self.handle_request(socket, node_id, address_maybe)
        else:
            # Can't do anything with this, drop.
            return

    def handle_discover(self, socket: Socket, node_id: UUID, address_maybe: Optional[Address]) -> None:
        if len(self._address_allocation) == self._num_hosts_max:
            # Network is full! Cannot allocate any more address (https://tools.ietf.org/html/rfc2131#section-4.3.1)
            return

        if address_maybe is not None and address_maybe not in self._address_allocation:
            suggestion = cast(Address, address_maybe)
        else:
            for _ in range(self._num_hosts_max):
                suggestion = next(self._seq_num_hosts)
                if suggestion not in self._address_allocation:
                    break
            else:
                # Decline to allocate as per https://tools.ietf.org/html/rfc2131#section-4.3.1
                # This should be redundant with the validation above
                return

        self._address_allocation[node_id] = _AddressAllocation(suggestion)
        socket.send(
            (self._cidr.broadcast_address, DHCP_CLIENT_PORT),
            LEN_PACKET_DHCP,
            cast(Payload, {
                Field.MESSAGE: DHCP.OFFER,
                Field.ADDRESS: suggestion,
                Field.SERVER: self._address_mine,
                Field.NODE_ID: node_id
            })
        )

        # Reserve for 30 seconds -- a REQUEST for the address must have been received by then.
        # Otherwise, drop the reservation.
        unique = self._address_allocation[node_id].unique
        advance(RESERVATION_TIME_SECONDS * S)
        if not self._address_allocation[node_id].is_confirmed and self._address_allocation[node_id].unique == unique:
            del self._address_allocation[node_id]

    def handle_request(self, socket: Socket, node_id: UUID, address_maybe: Optional[Address]) -> None:
        if address_maybe is None:
            return  # Never mind a REQUEST without an address.
        address = cast(Address, address_maybe)

        if node_id in self._address_allocation and address == self._address_allocation[node_id].address:
            # This REQUEST is proper, confirming the allocation of the address.
            self._address_allocation[node_id].is_confirmed = True
            socket.send(
                (address, DHCP_CLIENT_PORT),
                LEN_PACKET_DHCP,
                cast(Payload, {
                    Field.MESSAGE: DHCP.ACK,
                    Field.ADDRESS: address,
                    Field.NODE_ID: node_id,
                    Field.LEASE_DURATION: LEASE_DURATION
                })
            )
        else:
            # Spurious REQUEST! Drop.
            return


class DHCPClient(Daemon):

    def __init__(self, interface: Interface) -> None:
        super().__init__(self.run_client)
        self._interface = interface

    def run_client(self, thread: Thread) -> None:
        for _ in range(DHCP_CLIENT_RETRIES):
            # Retry after each failure to get an address.
            if self._dhcp_get_address(thread):
                break

    def _dhcp_iter_responses(self, socket: Socket, node_id: UUID, message: DHCP) -> Generator[Packet, None, None]:
        time_remaining = RESERVATION_TIME_SECONDS
        while time_remaining >= 0.0:
            time_before_recv = now()
            packet = socket.recv(time_remaining)
            time_remaining -= (now() - time_before_recv)
            if packet.payload.get(cast(str, Field.MESSAGE)) == message and \
               packet.payload.get(cast(str, Field.NODE_ID)) == node_id:
                yield packet

    def _dhcp_discover(self, socket: Socket, node_id: UUID, address_broadcast: Address) -> Optional[Address]:
        socket.send(
            (address_broadcast, DHCP_SERVER_PORT),
            LEN_PACKET_DHCP,
            cast(Payload, {Field.MESSAGE: DHCP.DISCOVER, Field.NODE_ID: node_id})
        )

        # Wait for our OFFER.
        for packet in self._dhcp_iter_responses(socket, node_id, DHCP.OFFER):
            if Field.ADDRESS in packet.payload:
                return cast(Address, packet.payload[cast(str, Field.ADDRESS)])

        return None

    def _dhcp_request(self,
                      socket: Socket,
                      node_id: UUID,
                      address_broadcast: Address,
                      address_proposed: Address) -> bool:
        socket.send(
            (address_broadcast, DHCP_SERVER_PORT),
            LEN_PACKET_DHCP,
            cast(Payload, {Field.MESSAGE: DHCP.REQUEST, Field.NODE_ID: node_id, Field.ADDRESS: address_proposed})
        )

        # Wait for our ACK.
        for packet in self._dhcp_iter_responses(socket, node_id, DHCP.ACK):
            if packet.dest.hostname_as_address() == address_proposed:
                return True
        return False

    def _dhcp_get_address(self, thread: Thread) -> bool:
        address_orig = self._interface.address
        node_id = thread.process.node.uuid
        try:
            broadcast_address = self._interface.cidr.broadcast_address
            with thread.process.node.bind(Protocol.UDP, DHCP_CLIENT_PORT, thread.process.pid) as socket:
                address = self._dhcp_discover(socket, node_id, broadcast_address)
                if address is not None:
                    self._interface.address = cast(Address, address)
                    if not self._dhcp_request(socket, node_id, broadcast_address, address):
                        self._interface.address = address_orig
                        return False
                    return True
                else:
                    return False
        except Timeout:
            return False
