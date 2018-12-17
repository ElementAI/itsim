from typing import Callable, Any, Generator

from itsim import ITObject
from itsim.machine import _Socket, _Node
from itsim.machine.process_management import _Process, _Thread
from itsim.simulator import Simulator
from itsim.types import Protocol, PortRepr, Address


class Context(ITObject):
    """
    Context from which executes a function expressing the behaviour of a piece of software within the simulation. This
    context encompasses information queries regarding the surrounding thread, process and node.

    :param thread:
        Thread associated to this software computation.
    """

    def __init__(self, thread: _Thread) -> None:
        super().__init__()
        self._thread = thread

    @property
    def thread(self) -> _Thread:
        """
        Thread object associated to this computation.
        """
        return self._thread

    @property
    def process(self) -> _Process:
        """
        Process to which belongs the thread associated to this computation.
        """
        return self.thread.process

    @property
    def node(self) -> _Node:
        """
        Node on which runs the process to which belongs the thread associated to this computation.
        """
        return self.process.node
