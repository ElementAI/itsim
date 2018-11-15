"""
This module contains the simulated representations of processes and threads.

Process objects are created the :py:meth:`fork_exec <itsim.machine.Node.fork_exec>`
or :py:meth:`fork_exec_in <itsim.machine.Node.fork_exec_in>`.
These will in turn call the :py:meth:`exc <itsim.machine.processes.Process.exc>`
and :py:meth:`exc_in <itsim.machine.processes.Process.exc_in>` methods of Process to create Threads.
Each Thread is a direct interface with the simulator, scheduling the functions it is passed
along with a callback to alert the thread that its task has been completed.
The Thread will then call back to the owning Process, which will call the owning Node once it is out
of Threads, allowing the objects to be cleaned up as their execution is completed.
In addition, A tree can be constructed at any instant in the simulation that lists
all running Threads in all Processes in all Nodes
"""

from abc import abstractmethod, abstractproperty

from itsim import AbstractITObject
from itsim.machine.__init__ import _Node


class _Daemon(AbstractITObject):
    pass


class _Process(AbstractITObject):

    @abstractmethod
    def thread_complete(self, t) -> None:
        pass

    @abstractproperty
    def node(self) -> _Node:
        pass


class _Service(AbstractITObject):
    pass


class _Thread(AbstractITObject):

    @abstractproperty
    def process(self) -> _Process:
        pass
