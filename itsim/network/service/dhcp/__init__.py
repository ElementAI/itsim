from enum import Enum, unique

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
