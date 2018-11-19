from .__init__ import _Process

from itsim.machine import _Node
from itsim.simulator import Simulator
from itsim.machine.process_management.thread import Thread
from itsim.types import Interrupt
from itsim.utils import assert_list

from typing import Any, Callable, Optional, Set


class Process(_Process):
    """
    Process objects hold a lot of information about their state and control the creation of Threads.
    They can also fork off new Processes and store them as children
    Once all of the Threads have completed the Process calls back to the Process Manager to exit
    """
    def __init__(self, n: int, node: _Node, parent: Optional[_Process] = None) -> None:
        super().__init__()
        self._children: Set[_Process] = set()
        self._parent: Optional[_Process] = parent
        self._threads: Set[Thread] = set()
        self._n: int = n
        self._node: _Node = node
        self._thread_counter: int = 0

    @property
    def children(self) -> Set[_Process]:
        return self._children

    def exc_in(self, sim: Simulator, time: float, f: Callable[[Thread], None], *args, **kwargs) -> Thread:
        t = Thread(sim, self, self._thread_counter)
        self._thread_counter += 1
        t.clone_in(time, f, *args, **kwargs)
        self._threads |= set([t])
        # Not generally useful. For unit tests
        return t

    def exc(self, sim: Simulator, f: Callable[[Thread], None], *args, **kwargs) -> Thread:
        return self.exc_in(sim, 0, f, *args, **kwargs)

    def thread_complete(self, t: Thread):
        self._threads -= set([t])
        if self._threads == set():
            if self._parent is not None:
                self._parent.child_complete(self)
            self._node.proc_exit(self)

    def child_complete(self, p: _Process):
        self._children -= set([p])

    def signal(self, sig: Interrupt) -> None:
        pass

    def kill(self) -> int:
        pass

    def fork_exec(self, f: Callable[[Thread], None], *args, **kwargs) -> _Process:
        kid = self._node.fork_exec(f, *args, **kwargs)
        kid._parent = self
        self._children |= set([kid])
        return kid

    def __eq__(self, other: Any) -> bool:
        # NB: MagicMock overrides the type definition and makes this check fail if _Process is replaced with Process
        if not isinstance(other, _Process):
            return False
        elif self is other:
            return True

        return assert_list([
            self._n == other._n,
            self._node == other._node])

    def __str__(self):
        return "(%s)" % ", ".join([str(y) for y in [
            self._children,
            self._parent,
            self._threads,
            self._n,
            self._node,
            self._thread_counter
        ]])

    def __hash__(self):
        return hash((self._n, self._node))
