from abc import ABC
from enum import auto
from typing import Callable
from uuid import uuid4, UUID

from greensim import tagged
from greensim.tags import Tags, TaggedObject


class Tag(Tags):
    MALWARE = auto()
    VULNERABLE = auto()


class ITObject(TaggedObject):

    def __init__(self, *tags: Tag) -> None:
        super().__init__(*tags)
        self._uuid = uuid4()

    @property
    def uuid(self) -> UUID:
        return self._uuid

    def uuid_str(self) -> str:
        return str(self._uuid)

    def __str__(self) -> str:
        return f"{type(self).__name__}{{{str(self.uuid)}}}"

    def __repr__(self) -> str:
        return str(self)

    def _bind_and_call_constructor(self, t: type, *args, **kwargs) -> None:
        """
        For a detailed description of why this is necessary and what it does see get_binding.md
        """
        t.__init__.__get__(self)(*args, **kwargs)  # type: ignore


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
