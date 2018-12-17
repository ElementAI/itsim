from typing import Callable, Any, Generator

from itsim import ITObject
from itsim.machine import _Socket, _Node
from itsim.machine.process_management import _Process, _Thread
from itsim.simulator import Simulator
from itsim.types import Protocol, PortRepr, Address


class Context(ITObject):
    """
    Context from which executes a function expressing the behaviour of a piece of software within the simulation. This
    context encompasses information queries regarding the surrounding thread, process and node, as well as common
    actions to enact the behaviours of interest.

    :param thread:
        Thread associated to this software computation.
    :sim:
        Simulator instance that supports the world in emulation.
    """

    def __init__(self, thread: _Thread, sim: Simulator) -> None:
        super().__init__()
        self._thread = thread
        self._sim = sim

    def exit(self) -> None:
        """
        Commands the current process to terminate immediately.
        """
        self.process.kill()

    def run_proc(self, fn: Callable[..., None], *args: Any, **kwargs: Any) -> _Process:
        """
        Runs a computation into a new process on the current node.

        :param fn:
            Function that implements this computation. Should take as first parameter a Context instance (which will
            be distinct from this one).

        Arguments provided beyond ``fn`` will be passed as arguments when invoking the function.
        """
        return self.run_proc_in(0, fn, *args, **kwargs)

    def run_proc_in(self, delay: float, fn: Callable[..., None], *args: Any, **kwargs: Any) -> _Process:
        """
        Runs a computation into a new process after the given delay has elapsed. See :py:meth:`run_proc`.
        """
        return self.node.run_proc_in(self._sim, delay, fn, *args, **kwargs)

    def run_thread(self, fn: Callable[..., None], *args: Any, **kwargs: Any) -> _Thread:
        """
        Runs a computation in a new thread from the current process.

        :param fn:
            Function that implements this computation. Should take as first parameter a Context instance (which will
            be distinct from this one).

        Arguments provided beyond ``fn`` will be passed as arguments when invoking the function.
        """
        return self.run_thread_in(0, fn, *args, **kwargs)

    def run_thread_in(self, delay: float, fn: Callable[..., None], *args: Any, **kwargs: Any) -> _Thread:
        """
        Runs a computation into a new thread from the current process. See :py:meth:`run_thread`.
        """
        return self.process.exc_in(self._sim, delay, fn, *args, **kwargs)

    def now(self) -> float:
        """
        Returns the current time on the simulation clock.
        """
        return self._sim.now()

    def bind(self, protocol: Protocol = Protocol.NONE, pr: PortRepr = 0) -> _Socket:
        """
        Binds a socket against the given protocol.

        :param protocol:
            Protocol associated to this socket's network transactions.
        :param pr:
            Optional port number to bind to. If no port number is provided, an ephemeral socket is allocated (if
            possible).
        """
        return self.node.bind(protocol, pr, self.process.pid)

    def addresses(self) -> Generator[Address, None, None]:
        """
        Provides an iterator through the IP addresses associated to the current node.
        """
        yield from self.node.addresses()

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
