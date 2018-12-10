from enum import Enum, unique
from uuid import UUID, uuid4

from itsim.types import Address
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
