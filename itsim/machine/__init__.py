from abc import abstractmethod, abstractproperty

from typing import Iterable, Callable

from itsim import AbstractITObject
from itsim.simulator import Simulator
from itsim.types import Address, PortRepr, Protocol


class _Node(AbstractITObject):
    pass
