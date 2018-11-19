from enum import Enum, unique, auto
from itertools import cycle
from typing import Optional, MutableMapping

from greensim.random import normal

from itsim.network import _Packet
from itsim.machine.node import Socket
from itsim.machine.process_management import _Thread
from itsim.machine.process_management.daemon import Daemon
from itsim.machine.process_management.thread import Thread
from itsim.network.link import Link
from itsim.random import num_bytes
from itsim.types import Address, as_address
from itsim.units import B


LEN_PACKET_DHCP = 348
LEASE = 86400


@unique
class DHCP(Enum):
    DISCOVER = auto()
    OFFER = auto()
    REQUEST = auto()
    ACK = auto()


@unique
class Field(Enum):
    MESSAGE = auto()
    NODE_ID = auto()
    ADDRESS = auto()
    LEASE = auto()
    SERVER = auto()


class AddressAllocation:

    def __init__(self, address: Address) -> None:
        self._address = address
        self._is_confirmed = False

    @property
    def address(self) -> Address:
        return self._address

    @property
    def is_confirmed(self) -> bool:
        return self._is_confirmed

    @is_confirmed.setter
    def is_confirmed(self, is_confirmed: bool) -> None:
        self._is_confirmed = is_confirmed


class DHCPDaemon(Daemon):
    responses = {"DHCPDISCOVER": "DHCPOFFER", "DHCPREQUEST": "DHCPACK"}
    size_packet_dhcp = num_bytes(normal(100.0 * B, 30.0 * B), header=240 * B)

    def __init__(self, num_host_first: int) -> None:
        super().__init__(self.on_packet)
        if num_host_first <= 0:
            raise ValueError(f"num_host first >= 1 (here {num_host_first})")
        self._num_host_first = num_host_first
        self._address_allocation: MutableMapping[str, Address] = {}

    def for_link(self, link: Link) -> None:
        self._cidr = link.cidr
        upper_num_host = int(self._cidr.hostmask)
        if self._num_host_first >= upper_num_host:
            raise ValueError(
                f"First host number is too high ({num_host_first}) for this link's CIDR; use " +
                f"{upper_num_host - 1} or lower."
            )
        self._num_hosts_max = upper_num_host - self._num_host_first
        self._seq_num_hosts = cycle(as_address(n, self._cidr) for n in range(self._num_host_first, upper_num_host))

    def init(self, link: Link, thread: Thread) -> None:
        for address in self.addresses():
            if address in self._cidr:
                self._address_mine = address
                break
        else:
            raise RuntimeError("DHCP server can only run on a node with its own address on the target link.")

    def on_packet(self, thread: _Thread, packet: _Packet, socket: Socket) -> None:
        payload = packet.payload
        if Field.MESSAGE not in payload or NODE_ID not in payload:
            # Don't bother processing ill-formed messages.
            return
        message = payload[Field.MESSAGE]
        node_id = payload[Field.NODE_ID]
        address_maybe = as_address(payload[Field.ADDRESS], self._cidr) if Field.ADDRESS in payload else None

        if message == DHCP.DISCOVER:
            handle_discover(socket, node_id, address_maybe)
        elif message == DHCP.REQUEST:
            handle_request(socket, node_id, address_maybe)
        else:
            # Can't do anything with this, drop.
            pass

    def handle_discover(self, node_id: str, address_maybe: Optional[Address]) -> None:
        if len(self._address_allocation) == self._num_hosts_max:
            # Network is full! Cannot allocate any more address.
            return

        if address is not None and address not in self._address_allocation:
            suggestion = cast(Address, address)
        else:
            for _ in range(self._num_hosts_max):
                suggestion = next(self._seq_num_hosts)
                if suggestion not in self._address_allocation:
                    break
            else:
                raise RuntimeError("Trying to allocate more addresses than the network can allow.")

        self._address_allocation[node_id] = AddressAllocation(suggestion)
        socket.send(
            (self._cidr.broadcast_address, 68),
            LEN_PACKET_DHCP,
            { Field.MESSAGE: DHCP.OFFER, Field.ADDRESS: suggestion, Field.SERVER: self._address_mine }
        )

        # Reserve for 30 seconds -- a REQUEST for the address must have been received by then.
        # Otherwise, drop the reservation.
        advance(30.0 * S)
        if not self._address_allocation[node_id].is_confirmed:
            del self._address_allocation[node_id]

    def handle_request(self, node_id: str, address_maybe: Optional[Address]) -> None:
        if address_maybe is None:
            return  # Never mind an offer without an address.
        address = cast(Address, address_maybe)

        if node_id in self._address_allocation and address == self._address_allocation[node_id]:
            # This REQUEST is proper, confirming the allocation of the address.
            self._address_allocation[node_id].is_confirmed = True
            socket.send(
                (address, 68),
                LEN_PACKET_DHCP,
                { Field.MESSAGE: DHCP.ACK, Field.ADDRESS: address, Field.LEASE: LEASE }
            )
        else:
            # Spurious REQUEST! Drop.
            return
