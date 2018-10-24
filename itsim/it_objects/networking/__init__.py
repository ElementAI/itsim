from abc import ABC, abstractmethod

from itsim import _Node
from itsim import ITObject
from itsim.types import AddressRepr


class _Link(ABC, ITObject):
    """
    This is an abstract superclass to Link that defines two externally visible methods, add_node and drop_node
    so that they can be used by other classes which must reference Link before it is defined, Node in particular.
    This allowd the Node class to depend on _Link (and the Link class to depend on _Node in turn) without
    breaking Python's type definition rules
    """
    def __init__(self):
        """
        Calls the constructors for ABC and ITObject with no arguments
        """
        self._bind_and_call_constructor(ABC)
        self._bind_and_call_constructor(ITObject)

    @abstractmethod
    def add_node(self, node: _Node, ar: AddressRepr) -> None:
        """
        Generic method for adding a Node to this _Link. It is defined in detail in Link
        """
        raise NotImplementedError("Meant to be subclassed")

    @abstractmethod
    def drop_node(self, ar: AddressRepr) -> bool:
        """
        Generic method for removing a Node from this _Link. It is defined in detail in Link
        """
        raise NotImplementedError("Meant to be subclassed")
