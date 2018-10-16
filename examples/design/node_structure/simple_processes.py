from abc import ABC, abstractmethod

from enum import Enum, unique

from greensim import now, advance

from itsim.it_objects import ITObject, Simulator

from typing import Callable, Optional, Set


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
    pass


class _Process(AbstractITObject):
    @abstractmethod
    def thread_complete(self, t) -> None:
        pass


class _ProcessManager(AbstractITObject):
    @abstractmethod
    def next_proc_number(self) -> int:
        pass


class _PMBuilder(AbstractITObject):
    pass


###################
#  Class mockups  #
###################
class Thread(_Thread):
    """
    This is the direct interface with the simulator. It wraps the function it is asked to schedule
    and sets up a callback to be notified when it is finished. This requires that, if the underlying
    simulator process schedules further events, they must do it through the owning Thread object
    (which is passed as the first argument), or the scheduled functions will not be tracked as part
    of the lifetime of the Thread (though they will happily run on their own without issue,
    oblivious to the confusion they cause)
    """
    def __init__(self, sim: Simulator, parent: _Process, n: int) -> None:
        super().__init__()
        self._sim: Simulator = sim
        self._process: _Process = parent
        self._n = n
        self._scheduled: Set[Callable[[], None]] = set()

    def clone_in(self, time: float, f: Callable[[_Thread], None], *args, **kwargs) -> None:
        log("Thread %s in process %s is being scheduled" % (self._n, self._process._n), Colors.GREEN)

        # Convenient object for putting in the tracking set
        def func() -> None:
            f(self, *args, **kwargs)  # type: ignore

        # Run the function as requested in arguments, then call back home
        def call_and_callback() -> None:
            func()
            self.exit_f(func)

        self._sim.add_in(time, call_and_callback)
        self._scheduled |= set([func])

    def clone(self, f: Callable[[_Thread], None], *args, **kwargs) -> None:
        self.clone_in(0, f, *args, **kwargs)

    def exit_f(self, f: Callable[[], None]) -> None:
        """
        Callback for functions that have completed. This drops them from the tracking set and,
        if the set is empty, calls back to the owning Process that this Thread is exiting
        """
        print("Exiting %s" % f.__hash__())
        self._scheduled -= set([f])
        print("Remaining Functions: %s" % ", ".join([str(fun.__hash__()) for fun in self._scheduled]))
        if self._scheduled == set():
            self._process.thread_complete(self)


class Process(_Process):
    """
    Process objects hold a lot of information about their state and control the creation of Threads.
    They can also fork off new Processes and store them as children
    Once all of the Threads have completed the Process calls back to the Process Manager to exit
    """
    def __init__(self, sim: Simulator, n: int, manager: _ProcessManager, parent: Optional[_Process] = None) -> None:
        super().__init__()
        self._sim: Simulator = sim
        self._children: Set[_Process] = set()
        self._parent: Optional[_Process] = parent
        self._threads: Set[Thread] = set()
        self._n: int = n
        self._manager: _ProcessManager = manager
        self._thread_counter: int = 0

    @property
    def children(self) -> Set[_Process]:
        return self._children

    def exc_in(self, time: float, f: Callable[[Thread], None], *args, **kwargs) -> None:
        t = Thread(self._sim, self, self._thread_counter)
        t.clone_in(time, f, *args, **kwargs)
        self._threads |= set([t])

    def exc(self, f: Callable[[Thread], None], *args, **kwargs) -> None:
        self.fork_in(0, f, *args, **kwargs)

    def thread_complete(self, t: Thread):
        log("Thread %s in process %s is closing" % (t._n, self._n), Colors.RED)
        self._threads -= set([t])
        print("Remaining Threads: %s" % ", ".join([str(thr.__hash__()) for thr in self._threads]))
        if self._threads == set():
            if self._parent is not None:
                self._parent.child_complete(self)
            self._manager.proc_exit(self)

    def child_complete(self, p: _Process):
        log("Child %s of process %s is closing" % (p._n, self._n), Colors.RED)
        self._children -= set([p])
        print("Remaining Children: %s" % ", ".join([str(pro.__hash__()) for pro in self._children]))

    def signal(self, sig: Interrupt) -> None:
        pass

    def kill(self) -> int:
        pass

    def fork_exc(self, f: Callable[[Thread], None], *args, **kwargs) -> _Process:
        kid = self._manager.fork_exc(f, *args, **kwargs)
        kid._parent = self
        self._children |= set([kid])
        return kid


class ProcessManager(ITObject):
    """
    This object represents some of the abilities of the operating system to manage processes.
    In this example it only keeps count, but it can be used to list running processes, manage
    ownership, and deliver signals.
    At any given interval, the attributes of this class, Process, and Thread can be used to
    construct a tree, with the Process Manager as the root node, pointing to every running
    Process, all of their Threads, and all of the scheduled events in the Thread
    """
    def __init__(self, sim: Simulator) -> None:
        super().__init__()
        self._sim: Simulator = sim
        self._proc_set: Set[Process] = set()
        self._process_counter: int = 0
        self._default_parent = Process(sim, -1, self)

    def procs(self) -> Set[Process]:
        return self._proc_set

    def fork_exc_in(self, time: float, f: Callable[[Thread], None], *args, **kwargs) -> Process:
        proc = Process(self._sim, self.next_proc_number(), self, self._default_parent)
        self._proc_set |= set([proc])
        proc.exc_in(time, f, *args, **kwargs)
        return proc

    def fork_exc(self, f: Callable[[Thread], None], *args, **kwargs) -> Process:
        return self.fork_exc_in(0, f, *args, **kwargs)

    def next_proc_number(self) -> int:
        self._process_counter += 1
        return self._process_counter - 1

    def proc_exit(self, p: Process) -> None:
        log("Process %s is closing" % p._n, Colors.RED)
        self._proc_set -= set([p])
        print("Remaining Procs: %s" % ", ".join([str(pro.__hash__()) for pro in self._proc_set]))


class PMBuilder(_PMBuilder):
    """
    Convenience for setting up ProcessManager objects
    """
    def __init__(self, sim: Simulator) -> None:
        super().__init__()
        self._sim: Simulator = sim
        self._pm = ProcessManager(sim)

    def with_proc_at(self, time: float, f: Callable[[Thread], None], *args, **kwargs) -> _PMBuilder:
        self._pm.fork_exc_in(time, f, *args, **kwargs)
        return self

    def build(self) -> ProcessManager:
        return self._pm


def run_sample() -> None:
    sim = Simulator()

    # Simple output for the child processes
    def short_kid(t: Thread):
        advance(10)
        log("I'm a child process! #%s > #%s" % (t._process._parent._n, t._process._n), Colors.YELLOW)

    # The optional argument just proves type checking works for the Process and Thread even with extra args
    def ping(thread: Thread, optional: object = None) -> None:
        proc = thread._process
        log("Howdy. It's %s O'clock" % now())
        log("\t I'm in process number %s" % proc._n)
        if proc._parent is not None:
            log("\t\t I'm a proud descendant of process %s" % proc._parent._n)
        log("\t\t I'm in thread  number %s" % thread._n)

        # Show off forking from withing a process
        proc.fork_exc(short_kid)

        # This just fills the function set in the Thread object to show that it works and how it looks
        thread.clone(lambda _: advance(1))
        thread.clone(lambda _: advance(1))

    # Builder patter for a priori setup of functions running at specific times
    pm = PMBuilder(sim).with_proc_at(1, ping).build()

    # Setting up a new process, forking it from outside, and setting up some concurrent threads
    proc = pm.fork_exc(ping)
    kid = proc.fork_exc(ping)
    kid.exc_in(1, ping)
    kid.exc_in(2, ping)
    kid.exc_in(3, ping)
    sim.run()


if __name__ == '__main__':
    run_sample()
