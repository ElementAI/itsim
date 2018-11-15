from .__init__ import _Service, _Thread

from typing import Callable

from itsim import _Node, ITObject
from itsim.simulator import Simulator


class Daemon(ITObject):
    """
    Base class for daemons, representing anything that runs every time some predetermined event occurs, the only
    argument to the constructor is a :py:class:`~typing.Callable`, taking any number of arguments. When
    :py:meth:`~trigger` is called, the :py:class:`~typing.Callable` is called with the arguments to
    :py:meth:`~trigger`, with no inspection. This makes Daemon a container for event-driven simulation logic

    :param trigger_event: The logic to be executed when this Daemon is triggered. This is not a simulation event
    """

    def __init__(self, trigger_event: Callable[..., None]):
        self._trigger_event = trigger_event

    def trigger(self, *args, **kwargs) -> None:
        self._trigger_event(*args, **kwargs)


class Service(_Service):
    """
    Base class for services, which contain a simulation event in the form of a :py:class:`~typing.Callable` which will
    be added to the simulation whenever :py:meth:`~call` is called. The :py:class:`~typing.Callable` should be passed to
    the constructor and should take at least one argument, a :py:class:`~itsim.node.process_management.thread.Thread`.
    When the :py:class:`~itsim.node.Node` that is passed to :py:meth:`~call` schedules and executes the
    :py:class:`~typing.Callable`, it will pass the :py:class:`~itsim.node.process_management.thread.Thread` that
    is managing it as the first argument.

    For a specific service (e.g., DHCP), this class can be subclassed and self._call_event can be fixed to
    a specific piece of logic

    :param call_event: The logic to be executed when this Daemon is triggered. This is not a simulation event
    """

    def __init__(self, call_event: Callable[[_Thread], object]):
        self._call_event = call_event

    def call(self, sim: Simulator, node: _Node, *args, **kwargs) -> None:
        node.fork_exec(sim, self._call_event, *args, **kwargs)
