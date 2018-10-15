from enum import Enum, unique
from typing import Dict
from itsim.it_objects import ITObject


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
