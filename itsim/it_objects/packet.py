from typing import Optional

from itsim import Location
from itsim.it_objects import ITObject
from itsim.it_objects.payload import Payload


class Packet(ITObject):

    def __init__(self, source: Location, dest: Location, byte_size: int, payload: Optional[Payload] = None) -> None:
        super().__init__()
        self._source = source
        self._dest = dest
        self._byte_size = byte_size
        self._payload = payload

    @property
    def source(self) -> Location:
        """
        Location object representing the place this Packet was sent from
        """
        return self._source

    @property
    def dest(self) -> Location:
        """
        Location object representing the place this Packet was sent to
        """
        return self._dest

    @property
    def byte_size(self) -> int:
        """
        Size of the packet in bytes
        """
        return self._byte_size

    @property
    def payload(self) -> Optional[Payload]:
        """
        Payload of the packet represented as a Dictionary of Tags and values. May be None
        """
        return self._payload
