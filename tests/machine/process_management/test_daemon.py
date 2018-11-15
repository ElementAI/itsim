from itsim.machine.process_management.daemon import Daemon, Service
from itsim.simulator import Simulator

from pytest import raises
from unittest.mock import patch

##########
# Daemon #
##########


def test_daemon_init():
    def f():
        pass

    daemon = Daemon(f)
    assert daemon._trigger_event == f


def test_trigger():
    class AdHocError(Exception):
        pass

    def f():
        raise AdHocError()

    daemon = Daemon(f)
    with raises(AdHocError):
        daemon.trigger()

    def g(arg, kwarg):
        if arg == 0 and kwarg == 1:
            raise AdHocError()

    daemon = Daemon(g)
    with raises(AdHocError):
        daemon.trigger(0, kwarg=1)

###########
# Service #
###########


def test_service_init():
    def f():
        pass

    service = Service(f)
    assert service._call_event == f


@patch("itsim.machine.node.Node")
def test_call(mock_node):
    def f():
        pass

    service = Service(f)
    sim = Simulator()
    args = (1, 2, 3)
    kwargs = {"a": 0, "b": 1}
    service.call(sim, mock_node, *args, **kwargs)
    mock_node.fork_exec.assert_called_with(sim, f, *args, **kwargs)
