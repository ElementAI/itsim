from abc import ABC
from typing import Callable, cast, MutableMapping, Type, TypeVar
from uuid import uuid4, UUID

from greensim import tagged
from greensim.tags import Tags, TaggedObject


class Tag(Tags):
    MALWARE = 0
    VULNERABLE = 1


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


# As per https://mypy.readthedocs.io/en/latest/metaclasses.html#metaclass-usage-example
T = TypeVar('T')


# This is a metaclass. For more information, see
# https://docs.python.org/3/reference/datamodel.html?highlight=metaclass#metaclasses
#
# This implementation was adapted from https://stackoverflow.com/questions/6760685/creating-a-singleton-in-python
class Singleton(type):
    """
    Metaclass to define an arbitrary class as singleton. Any class with "metaclass=Singleton" in the header
    will show singleton behavior in its constructor. I.e., all calls to the constructor will return the same
    instance, until `reset` is called
    """
    # Global map of Singleton types to their single instances (or lack thereof)
    # N.B. This can be accessed through Singleton._instances or type(obj)._instances where obj has Singleton
    # as a metaclass. This fact is used in this implementation to aid typechecking
    _instances: MutableMapping[type, object] = {}

    # Since this is a metaclass, __call__ is called on construction of the class where this is applied
    # (like __init__ in a superclass)
    def __call__(cls: Type[T], *args, **kwargs) -> T:
        # If no instance has yet been created
        if cls not in Singleton._instances:
            # super(Singleton, cls) returns the type (not the class) cls
            # __call__(*args, **kwargs) calls the constructor (exactly like o = object())
            Singleton._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
        return cast(T, Singleton._instances[cls])

    # Drop the Singleton instance of cls
    def reset(cls: "Singleton") -> None:
        """
        Remove the Singleton metaclass reference to cls, if it exists. N.B. this does not guaruntee that there will be
        no references to the instance of cls, if it existed. This only drops the reference in Singleton, meaning the
        next call to the constructor of cls will call __init__ and return a new object

        :param cls: The type to reset
        """
        if cls in Singleton._instances:
            del Singleton._instances[cls]

    def has_instance(cls: "Singleton") -> bool:
        """
        Check for the existance of an instance of cls

        :param cls: The type to check
        """
        return cls in cls._instances


def malware(event: Callable) -> Callable:
    """
    Convenience decorator for identifying malware.
    Through the methods in greensim this label is cascaded through the actions of the Process
    """
    return tagged(Tag.MALWARE)(event)
