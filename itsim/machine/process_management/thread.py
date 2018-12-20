from .__init__ import _Thread, _Process

from itsim.software.context import Context
from itsim.simulator import Simulator, Event, SimulatedComputation, Interrupt, advance
from itsim.utils import assert_list

from typing import Any, Callable, Set, Tuple, Optional


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
        self._process: _Process = parent
        self._n: int = n
        self._computations: Set[SimulatedComputation] = set()
        self._event_dead = Event()

    @property
    def process(self) -> _Process:
        return self._process

    def clone_in(self, time: float, f: Callable[..., None], *args: Any, **kwargs: Any) -> "Thread":
        return self.process.exc_in(self._sim, time, f, *args, **kwargs)

    def clone(self, f: Callable[..., None], *args: Any, **kwargs: Any) -> "Thread":
        return self.clone_in(0, f, *args, **kwargs)

    def run_in(self, time: float, f: Callable[..., None], *args, **kwargs) -> Tuple[SimulatedComputation, Callable]:
        def wrap_computation(sim_comp, delay) -> None:
            try:
                # We use advance() here instead of using the simulator's add_in() method. This enables starting the
                # computation right away. Thereby, killing it raises the exception during the execution of this
                # function to trigger the finally block.
                advance(delay)
                f(Context(self), *args, **kwargs)  # type: ignore
            finally:
                self.exit_f(sim_comp)

        sim_comp = SimulatedComputation()
        sim_comp.gp = self._sim.add(wrap_computation, sim_comp, time)
        self._computations.add(sim_comp)

        # Not generally useful. For unit tests
        return (sim_comp, wrap_computation)

    def run(self, f: Callable[..., None], *args, **kwargs) -> Tuple[SimulatedComputation, Callable]:
        return self.run_in(0, f, *args, **kwargs)

    def exit_f(self, sim_comp: SimulatedComputation) -> None:
        """
        Callback for functions that have completed. This drops them from the tracking set and,
        if the set is empty, calls back to the owning Process that this Thread is exiting
        """
        self._computations.remove(sim_comp)
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
        """
        Kills a thread. :py:meth:`join` it to wait for its complete termination.

        Killing a thread causes all of its computations to be interrupted using the :py:class:`ThreadKilled` interrupt,
        which can be caught by computations as an exception, and discarded altogether. It is thus good style to avoid
        causing undue delay in computations thus embedded into a :py:class:`Thread` -- any other thread waiting on its
        termination is blocked until such computations have completed. Only *then* is the thread considered dead, and
        any other thread waiting on its termination (through method :py:meth:`join`) is resumed.
        """
        for sim_comp in self._computations:
            sim_comp.gp.interrupt(ThreadKilled())

    def join(self, timeout: Optional[float] = None) -> None:
        """
        Blocks until this thread has terminated, either naturally or from being :py:meth:`kill` ed. If a timeout is
        provided, failure of the thread to terminate before this timeout has elapsed (in simulator time) results in
        exception :py:class:`~itsim.types.Timeout` being raised.
        """
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
