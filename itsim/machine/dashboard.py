from typing import Callable, Any, Generator

from itsim import ITObject
from itsim.machine import _Socket, _Node
from itsim.machine.process_management import _Process, _Thread
from itsim.simulator import Simulator
from itsim.types import Protocol, PortRepr, Address


class Dashboard(ITObject):

    def __init__(self, thread: _Thread, sim: Simulator) -> None:
        super().__init__()
        self._thread = thread
        self._sim = sim

    def exit(self) -> None:
        self.process.kill()

    def run_proc(self, fn: Callable[..., None], *args: Any, **kwargs: Any) -> _Process:
        return self.run_proc_in(0, fn, *args, **kwargs)

    def run_proc_in(self, delay: float, fn: Callable[..., None], *args: Any, **kwargs: Any) -> _Process:
        return self.node.run_proc_in(self._sim, delay, fn, *args, **kwargs)

    def run_thread(self, fn: Callable[..., None], *args: Any, **kwargs: Any) -> _Thread:
        return self.run_thread_in(0, fn, *args, **kwargs)

    def run_thread_in(self, delay: float, fn: Callable[..., None], *args: Any, **kwargs: Any) -> _Thread:
        return self.process.exc_in(self._sim, delay, fn, *args, **kwargs)

    def now(self) -> float:
        return self._sim.now()

    def bind(self, protocol: Protocol = Protocol.NONE, pr: PortRepr = 0) -> _Socket:
        return self.node.bind(protocol, pr, self.process.pid)

    def addresses(self) -> Generator[Address, None, None]:
        yield from self.node.addresses()

    @property
    def thread(self) -> _Thread:
        return self._thread

    @property
    def process(self) -> _Process:
        return self.thread.process

    @property
    def node(self) -> _Node:
        return self.process.node
