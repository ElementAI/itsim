from typing import Callable, Any, Optional

from itsim import ITObject
from itsim.machine.process_management import _Process, _Thread
from itsim.simulator import Simulator


class API(ITObject):

    def __init__(self, thread: _Thread, sim: Simulator) -> None:
        super().__init__()
        self._thread = thread
        self._sim = sim

    def exit(self) -> None:
        pass

    def run_proc(self, fn: Callable[..., None], *args: Any, **kwargs: Any) -> _Process:
        pass

    def run_proc_in(self, delay: float, fn: Callable[..., None], *args: Any, **kwargs: Any) -> _Process:
        pass

    def wait_proc(self, timeout: Optional[float] = None) -> _Process:
        pass

    def run_thread(self, fn: Callable[..., None], *args: Any, **kwargs: Any) -> _Thread:
        pass

    def run_thread_in(self, delay: float, fn: Callable[..., None], *args: Any, **kwargs: Any) -> _Thread:
        pass

    def now(self) -> float:
        return self._sim.now()
