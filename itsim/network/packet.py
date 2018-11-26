from typing import Optional

from itsim import ITObject
from itsim.network.location import Location
from itsim.types import Payload


class Packet(ITObject):
    """
    Embodiment of a packet of data relayed over a link managed as a IP network.

    :param source: Source location of the packet.
    :param dest: Destination location where the packet is being relayed.
    :byte_size: Size of the packet's payload, in bytes.
    :payload: Optional free-form dictionary used as a helper for implementing certain models. Not used by ITsim.
    """

    def __init__(self,
                 source: Location,
                 dest: Location,
                 byte_size: int,
                 payload: Optional[Payload] = None) -> None:
        super().__init__()
        self._source = source
        self._dest = dest
        self._byte_size = byte_size
        self._payload = payload or {}

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
    def payload(self) -> Payload:
        """
        Payload of the packet represented as a Dictionary of Enum members and arbitrary values

        Defaults to a payload with an empty dictionary
        """
        return self._payload

    def __len__(self) -> int:
        """
        Convenience method to give the Packet a notion of size
        """
        return self._byte_size

    # Mainly for testing
    def __eq__(self, other) -> bool:

        if other is None:
            return False

        if not isinstance(other, Packet):
            return False

        return self.source == other.source \
            and self.dest == other.dest \
            and self.byte_size == other.byte_size \
            and self.payload == other.payload

    def __str__(self):
        return "<Src: %s, Dest: %s, Size: %s, Payload: %s>" % (self.source, self.dest, self.byte_size, self.payload)
