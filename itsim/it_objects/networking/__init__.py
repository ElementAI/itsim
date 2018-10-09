from abc import ABC, abstractmethod

from itsim import _Node
from itsim.it_objects import ITObject
from itsim.types import AddressRepr


class _Link(ABC, ITObject):

    def __init__(self):
        self._bind_and_call_constructor(ABC)
        self._bind_and_call_constructor(ITObject)

    @abstractmethod
    def add_node(self, node: _Node, ar: AddressRepr) -> None:
        raise NotImplementedError("Meant to be subclassed")

    @abstractmethod
    def drop_node(self, ar: AddressRepr) -> bool:
        raise NotImplementedError("Meant to be subclassed")
