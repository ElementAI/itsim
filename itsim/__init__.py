from abc import ABC
from typing import Callable
from uuid import uuid4, UUID

from greensim import tagged
from greensim.tags import Tags, TaggedObject


class Tag(Tags):
    MALWARE = 0
    VULNERABLE = 1


class ITObject(TaggedObject):

    def __init__(self, *tags) -> None:
        super().__init__(*tags)
        self._uuid = uuid4()

    @property
    def uuid(self) -> UUID:
        return self._uuid

    def _bind_and_call_constructor(self, t: type, *args) -> None:
        """
        For a detailed description of why this is necessary and what it does see get_binding.md
        """
        t.__init__.__get__(self)(*args)  # type: ignore


class AbstractITObject(ABC, ITObject):
    """
    Convenience class for managing multiple inheritance from ABC and ITObject.
    """
    def __init__(self):
        """
        Calls the constructors for ABC and ITObject with no arguments
        """
        self._bind_and_call_constructor(ABC)
        self._bind_and_call_constructor(ITObject)


def malware(event: Callable) -> Callable:
    """
    Convenience decorator for identifying malware.
    Through the methods in greensim this label is cascaded through the actions of the Process
    """
    return tagged(Tag.MALWARE)(event)
