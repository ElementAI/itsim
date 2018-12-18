from .__init__ import _Thread

from itsim.software.context import Context
from itsim.simulator import Simulator, Event, SimulatedComputation, Interrupt
from itsim.utils import assert_list

from typing import Any, Callable, Dict, Tuple, Optional


class ThreadKilled(Interrupt):
    pass


class Thread(_Thread):
    """
    This is the direct interface with the simulator. It wraps the function it is asked to schedule
    and sets up a callback to be notified when it is finished. This requires that, if the underlying
    simulator process schedules further events, they must do it through the owning Thread object
    (which is passed as the first argument), or the scheduled functions will not be tracked as part
    of the lifetime of the Thread (though they will happily run on their own without issue,
    oblivious to the confusion they cause)
    """
    def __init__(self, sim: Simulator, parent: SimulatedComputation, n: int) -> None:
        super().__init__()
        self._sim: Simulator = sim
        self._process: SimulatedComputation = parent
        self._n: int = n
        self._computations: Dict[Callable[..., None], SimulatedComputation] = {}
        self._event_dead = Event()

    @property
    def process(self) -> SimulatedComputation:
        return self._process

    def clone_in(self, time: float, f: Callable[..., None], *args: Any, **kwargs: Any) -> "Thread":
        return self.process.exc_in(self._sim, time, f, *args, **kwargs)

    def clone(self, f: Callable[..., None], *args: Any, **kwargs: Any) -> "Thread":
        return self.clone_in(0, f, *args, **kwargs)

    def run_in(self, time: float, f: Callable[[_Thread], None], *args, **kwargs) -> Tuple[Callable, Callable]:
        # Convenient object for putting in the tracking set
        def func() -> None:
            f(Context(self), *args, **kwargs)  # type: ignore

        # Run the function as requested in arguments, then call back home
        def call_and_callback() -> None:
            try:
                func()
            finally:
                self.exit_f(func)

        self._computations[func] = self._sim.add_in(time, call_and_callback)
        # Not generally useful. For unit tests
        return (func, call_and_callback)

    def run(self, f: Callable[..., None], *args, **kwargs) -> Tuple[Callable[[], None], Callable[[], None]]:
        return self.run_in(0, f, *args, **kwargs)

    def exit_f(self, f: Callable[..., None]) -> None:
        """
        Callback for functions that have completed. This drops them from the tracking set and,
        if the set is empty, calls back to the owning Process that this Thread is exiting
        """
        del self._computations[f]
        if len(self._computations) == 0:
            self._process.thread_complete(self)
            self._event_dead.fire()

    def __eq__(self, other: Any) -> bool:
        # NB: MagicMock overrides the type definition and makes this check fail if _Thread is replaced with Thread
        if not isinstance(other, _Thread):
            return False
        elif self is other:
            return True

        return assert_list([
            self._sim == other._sim,
            self._process == other._process,
            self._n == other._n])

    def is_alive(self) -> bool:
        return not self._event_dead.has_fired()

    def kill(self) -> None:
        for sim_comp in self._computations.values():
            sim_comp.interrupt(ThreadKilled())

    def join(self, timeout: Optional[float] = None) -> None:
        self._event_dead.wait(timeout)

    def __str__(self):
        return "(%s)" % ", ".join([str(y) for y in [
            self._sim,
            self._process.pid,
            self._n,
            self._computations
        ]])

    def __hash__(self):
        return hash((self._sim, self._process, self._n))
