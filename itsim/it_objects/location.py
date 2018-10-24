from functools import total_ordering
from ipaddress import _BaseAddress
from typing import cast, Any

from itsim.it_objects import ITObject
from itsim.types import Address, as_hostname, as_port, Hostname, HostnameRepr, Port, PortRepr


@total_ordering
class Location(ITObject):
    """
    Location of a service on a network, designated by a host name and a port number.

    :param host: Hostname representation.
    :param port: Port representation.
    """

    def __init__(self, host: HostnameRepr = None, port: PortRepr = None) -> None:
        super().__init__()
        self._hostname = as_hostname(host)
        self._port = as_port(port)

    @property
    def hostname(self) -> Hostname:
        """
        Returns the hostname of this location.
        """
        return self._hostname

    @property
    def port(self) -> Port:
        """
        Returns the port of this location.
        """
        return self._port

    def hostname_as_address(self) -> Address:
        """
        Provided the hostname corresponds to a duly formed IP address, this returns the address object corresponding to
        the location's hostname.
        """
        if not isinstance(self.hostname, _BaseAddress):
            raise ValueError("Location carries a domain name for host, which resolution must be simulated explicitly.")
        return cast(Address, self._hostname)

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, Location):
            raise ValueError(f"Cannot compare for equality {str(self)} to {str(other)} (type {type(other)}).")
        return self.hostname == other.hostname and self.port == other.port

    def __str__(self) -> str:
        return f"{str(self.hostname)}:{str(self.port)}"

    def __repr__(self) -> str:
        return repr(str(self))

    def __hash__(self) -> int:
        return hash(str(self))

    def __lt__(self, other) -> bool:
        if not isinstance(other, Location):
            raise ValueError(f"Cannot compare for order {str(self)} to {str(other)} (type {type(other)}).")
        if self.hostname == other.hostname:
            return self.port < other.port
        return str(self.hostname) < str(other.hostname)
