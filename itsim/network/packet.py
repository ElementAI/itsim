from enum import Enum, unique
from typing import Dict, Optional

from itsim import _Packet, ITObject
from itsim.network.location import Location


@unique
class PayloadDictionaryType(Enum):
    CONTENT = 0
    CONTENT_TYPE = 1
    HOSTNAME = 2
    ADDRESS = 3


class Payload(ITObject):

    def __init__(self, entries: Dict[PayloadDictionaryType, object] = {}) -> None:
        super().__init__()
        self._entries = entries

    @property
    def entries(self) -> Dict[PayloadDictionaryType, object]:
        return self._entries

    # Mainly for testing
    def __eq__(self, other) -> bool:
        if other is None:
            return False

        if not isinstance(other, Payload):
            return False

        return self._entries == other._entries

    def __str__(self):
        return "<%s>" % ", ".join(["%s: %s" % (k, v) for k, v in self.entries.items()])


class Packet(_Packet):
    """
    Embodiment of a packet of data relayed over a link managed as a IP network.

    :param source: Source location of the packet.
    :param dest: Destination location where the packet is being relayed.
    :byte_size: Size of the packet's payload, in bytes.
    :payload: Optional free-form data used as a helper for implementing certain models. Not used by ITsim.
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
        self._payload = payload or Payload()

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

    def __repr__(self):
        return repr(str(self))
