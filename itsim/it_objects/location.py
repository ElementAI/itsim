from functools import total_ordering
from ipaddress import _BaseAddress
from typing import cast, Any

from itsim.it_objects import ITObject
from itsim.types import Address, as_host, as_port, Host, HostRepr, Port, PortRepr


@total_ordering
class Location(ITObject):
    def __init__(self, host: HostRepr = None, port: PortRepr = None) -> None:
        super().__init__()
        self._host = as_host(host)
        self._port = as_port(port)

    @property
    def host(self) -> Host:
        return self._host

    @property
    def port(self) -> Port:
        return self._port

    def host_as_address(self) -> Address:
        if not isinstance(self.host, _BaseAddress):
            raise ValueError("Location carries a domain name for host, which resolution must be simulated explicitly.")
        return cast(Address, self._host)

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, Location):
            raise ValueError(f"Cannot compare for equality {str(self)} to {str(other)} (type {type(other)}).")
        return self.host == other.host and self.port == other.port

    def __str__(self) -> str:
        return f"{str(self.host)}:{str(self.port)}"

    def __repr__(self) -> str:
        return repr(str(self))

    def __hash__(self) -> int:
        return hash(str(self))

    def __lt__(self, other) -> bool:
        if not isinstance(other, Location):
            raise ValueError(f"Cannot compare for order {str(self)} to {str(other)} (type {type(other)}).")
        if self.host == other.host:
            return self.port < other.port
        return str(self.host) < str(other.host)
