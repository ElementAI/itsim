from itsim.it_objects import Simulator
from itsim.node import _Node
from itsim.node.processes import _Process
from itsim.node.processes.thread import Thread
from itsim.types import Interrupt

from typing import Callable, Optional, Set

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

    def exc_in(self, sim: Simulator, time: float, f: Callable[[Thread], None], *args, **kwargs) -> None:
        t = Thread(sim, self, self._thread_counter)
        t.clone_in(time, f, *args, **kwargs)
        self._threads |= set([t])

    def exc(self, f: Callable[[Thread], None], *args, **kwargs) -> None:
        self.fork_in(0, f, *args, **kwargs)

    def thread_complete(self, t: Thread):
        self._threads -= set([t])
        print("Remaining Threads: %s" % ", ".join([str(thr.__hash__()) for thr in self._threads]))
        if self._threads == set():
            if self._parent is not None:
                self._parent.child_complete(self)
            self._node.proc_exit(self)

    def child_complete(self, p: _Process):
        self._children -= set([p])
        print("Remaining Children: %s" % ", ".join([str(pro.__hash__()) for pro in self._children]))

    def signal(self, sig: Interrupt) -> None:
        pass

    def kill(self) -> int:
        pass

    def fork_exc(self, f: Callable[[Thread], None], *args, **kwargs) -> _Process:
        kid = self._node.fork_exc(f, *args, **kwargs)
        kid._parent = self
        self._children |= set([kid])
        return kid
