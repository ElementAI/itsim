from abc import ABC, abstractmethod

from enum import Enum, unique

from greensim import now

from itsim.it_objects import ITObject, Simulator

from typing import Callable, List, Optional, Set


@unique
class Colors(Enum):
    RED = '\033[31m'
    GREEN = '\033[32m'
    YELLOW = '\033[33m'
    CLOSE = '\033[0m'


def log(msg: str, color: Colors = None) -> None:
    if color is not None:
        msg = color.value + msg + Colors.CLOSE.value
    print(msg)


class SystemCall(ABC):
    """
    Under construction. Since OS functions are being captured in Node, I think it is likely that these will need
    to be implemented specifically.

    Not used in this demo.
    """
    @abstractmethod
    def make_call(self):
        pass


@unique
class Interrupt(Enum):
    """
    Under construction. This borrows from the UNIX convention of numbering the signals.

    Not used in this demo.
    """
    SIGINT = 0
    SIGKILL = 1


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


#######################################################################################
#  Several ABC's to allow proper type-checking with all of the ciruclar dependencies  #
#######################################################################################
class _Thread(AbstractITObject):
    def __init__(self) -> None:
        super().__init__()


class _Process(AbstractITObject):
    def __init__(self) -> None:
        super().__init__()

    @abstractmethod
    def thread_complete(self, t) -> None:
        pass


class _ProcessManager(AbstractITObject):
    def __init__(self) -> None:
        super().__init__()

    @abstractmethod
    def next_proc_number(self) -> int:
        pass


class _PMBuilder(AbstractITObject):
    def __init__(self) -> None:
        super().__init__()


##################
#  Class mockups #
##################
class Thread(_Thread):
    """
    Represent a thread with a callable object that blindly carries out it's assigned task
    In practice, this is just labels on a function. The function is required to take a Process
    as the first argument and a Thread as the second so that forks and thread creation
    can be performed
    """
    def __init__(self, f: Callable[[_Process, _Thread], None], parent: _Process, n: int) -> None:
        super().__init__()
        self._f = f
        self._parent: _Process = parent
        self._n = n

    def __call__(self, *args, **kwargs) -> None:
        self._f(*args, **kwargs)  # type: ignore
        self._parent.thread_complete(self)


class Process(_Process):
    """
    Process objects hold a lot of information about their state and control the creation of Threads.
    They can also fork off new Processes and store them as children
    For now, Threads are just functions that are run directly in a Greensim simulation
    """
    def __init__(self, sim: Simulator, n: int, manager: _ProcessManager, parent: Optional[_Process] = None) -> None:
        super().__init__()
        self._sim: Simulator = sim
        self._children: List[_Process] = []
        self._parent: Optional[_Process] = parent
        self._threads: Set[Thread] = set()
        self._n: int = n
        self._manager: _ProcessManager = manager
        self._thread_counter: int = 0

    @property
    def children(self) -> List[_Process]:
        return self._children

    def schedule_in(self, time: float, f: Callable[[_Process, Thread], None], *args, **kwargs) -> None:
        t = Thread(f, self, self._thread_counter)
        log("Thread %s in process %s is being scheduled" % (t._n, self._n), Colors.GREEN)
        self._thread_counter += 1
        self._sim.add_in(time, t, self, t, *args, **kwargs)
        self._threads |= set([t])

    def schedule(self, f: Callable[[_Process, Thread], None], *args, **kwargs) -> None:
        self.schedule_in(0, f, *args, **kwargs)

    def thread_complete(self, t: Thread):
        log("Thread %s in process %s is closing" % (t._n, self._n), Colors.RED)
        self._threads -= set([t])

    def signal(self, sig: Interrupt) -> None:
        pass

    def kill(self) -> int:
        pass

    def fork(self) -> _Process:
        kid = Process(self._sim, self._manager.next_proc_number(), self._manager, self)
        self._children.append(kid)
        return kid


class ProcessManager(ITObject):
    """
    This object represents some of the abilities of the operating system to manage processes.
    In this example it only keeps count, but it can be used to list running processes, manage
    ownership, and deliver signals
    """
    def __init__(self, sim: Simulator) -> None:
        super().__init__()
        self._sim: Simulator = sim
        self._proc_list: List[Process] = []
        self._process_counter: int = 0

    def proc_list(self) -> List[Process]:
        return self._proc_list

    def new_proc_in(self, time: float, f: Callable[[Process, Thread], None], *args, **kwargs) -> Process:
        proc = Process(self._sim, self.next_proc_number(), self)
        self._proc_list.append(proc)
        proc.schedule_in(time, f, *args, **kwargs)
        return proc

    def new_proc(self, f: Callable[[Process, Thread], None], *args, **kwargs) -> Process:
        return self.new_proc_in(0, f, *args, **kwargs)

    def next_proc_number(self) -> int:
        self._process_counter += 1
        return self._process_counter - 1


class PMBuilder(_PMBuilder):
    """
    Convenience for setting up ProcessManager objects
    """
    def __init__(self, sim: Simulator) -> None:
        super().__init__()
        self._sim: Simulator = sim
        self._pm = ProcessManager(sim)

    def with_proc_at(self, time: float, f: Callable[[Process, Thread], None], *args, **kwargs) -> _PMBuilder:
        self._pm.new_proc_in(time, f, *args, **kwargs)
        return self

    def build(self) -> ProcessManager:
        return self._pm


def run_sample() -> None:
    sim = Simulator()

    # The optional argument just proves type checking works for the Process and Thread even with extra args
    def ping(proc: Process, thread: Thread, optional: object = None) -> None:
        log("Howdy. It's %s O'clock" % now())
        log("\t I'm in process number %s" % proc._n)
        if proc._parent is not None:
            log("\t\t I'm a proud descendant of process %s" % proc._parent._n)
        log("\t\t I'm in thread  number %s" % thread._n)

        if proc._n < 10:
            proc.fork().schedule_in(10,
                                    lambda p, t: log("I'm a child process! #%s > #%s" % (p._parent._n, p._n),
                                                     Colors.YELLOW))

    pm = PMBuilder(sim).with_proc_at(1, ping).build()

    proc = pm.new_proc(ping)
    kid = proc.fork()
    kid.schedule_in(1, ping)
    kid.schedule_in(2, ping)
    kid.schedule_in(3, ping)
    sim.run()


if __name__ == '__main__':
    run_sample()
