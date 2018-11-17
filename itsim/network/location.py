from functools import total_ordering
from ipaddress import _BaseAddress
from typing import Any, cast, Union, Tuple

from itsim import ITObject
from itsim.types import Address, HostnameRepr, PortRepr, as_hostname, as_port, Hostname, Port


LocationRepr = Union["Location", Tuple[HostnameRepr, PortRepr]]


class AddressError(Exception):
    """
    Generic superclass for Exception objects that refer to an issue with a specific address
    """

    def __init__(self, value: Any) -> None:
        super().__init__()
        self.value_for_address = value


class AddressInUse(AddressError):
    """
    Indicates that the address requested is already in use by the class that threw the Exception
    This is a non-fatal event and can be safely handled at runtime, occasionally with a retry
    """
    pass


class InvalidAddress(AddressError):
    """
    Indicates that the address requested is not a valid IP address
    This is non-fatal in general, but also should not be retried with the same address
    """
    pass


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

    @staticmethod
    def from_repr(lr: LocationRepr) -> "Location":
        if isinstance(lr, Location):
            return cast(Location, lr)
        else:
            hr, pr = cast(Tuple[HostnameRepr, PortRepr], lr)
            return Location(hr, pr)

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
