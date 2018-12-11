from itsim.machine.dashboard import Dashboard
from itsim.machine.process_management.process import Process
from itsim.machine.process_management.thread import Thread
from itsim.simulator import Simulator
from itsim.utils import assert_list

from pytest import fixture, raises
from unittest.mock import patch


@fixture
@patch("itsim.machine.node.Node")
def proc(mock_node):
    return Process(0, mock_node)


@fixture
@patch("itsim.machine.process_management.process.Process")
def thread(mock_proc):
    return Thread(Simulator(), mock_proc, 0)


def test_init(proc):
    sim = Simulator()
    n = 0
    thread = Thread(sim, proc, n)
    assert_list([
        sim == thread._sim,
        proc == thread._process,
        n == thread._n,
        set() == thread._scheduled],
        throw=True)


@patch("itsim.machine.process_management.process.Process")
def test_eq(mock_proc, thread, proc):
    assert thread == thread

    sim = Simulator()
    assert Thread(sim, mock_proc, 0) == Thread(sim, mock_proc, 0)

    assert_list([
        Thread(sim, mock_proc, 0) != Thread(Simulator(), mock_proc, 0),
        Thread(sim, mock_proc, 0) != Thread(sim, proc, 0),
        Thread(sim, mock_proc, 0) != Thread(sim, mock_proc, 1)],
        throw=True)


@patch("itsim.machine.process_management.process.Process")
def test_hash(mock_proc, thread, proc):
    assert hash(thread) == hash(thread)

    sim = Simulator()
    assert hash(Thread(sim, mock_proc, 0)) == hash(Thread(sim, mock_proc, 0))

    assert_list([
        hash(Thread(sim, mock_proc, 0)) != hash(Thread(Simulator(), mock_proc, 0)),
        hash(Thread(sim, mock_proc, 0)) != hash(Thread(sim, proc, 0)),
        hash(Thread(sim, mock_proc, 0)) != hash(Thread(sim, mock_proc, 1))],
        throw=True)


@patch("itsim.simulator.Simulator")
def test_clone_in(mock_sim, proc):
    thread = Thread(mock_sim, proc, 0)
    t = 10

    (f_a, ccb_a) = thread.clone_in(t, lambda: 0)
    mock_sim.add_in.assert_called_with(t, ccb_a)
    assert thread._scheduled == set([f_a])

    (f_b, ccb_b) = thread.clone_in(t, lambda: 1)
    mock_sim.add_in.assert_called_with(t, ccb_b)
    assert thread._scheduled == set([f_a, f_b])


@patch("itsim.simulator.Simulator")
def test_clone(mock_sim, proc):
    thread = Thread(mock_sim, proc, 0)

    (f_a, ccb_a) = thread.clone(lambda: 0)
    mock_sim.add_in.assert_called_with(0, ccb_a)
    assert thread._scheduled == set([f_a])

    (f_b, ccb_b) = thread.clone(lambda: 1)
    mock_sim.add_in.assert_called_with(0, ccb_b)
    assert thread._scheduled == set([f_a, f_b])


@patch("itsim.simulator.Simulator")
@patch("itsim.machine.process_management.process.Process")
def test_exit_f(mock_sim, mock_proc):
    thread = Thread(mock_sim, mock_proc, 0)

    (f_a, _) = thread.clone(lambda: 0)
    thread.exit_f(f_a)
    assert thread._scheduled == set()
    mock_proc.thread_complete.assert_called_with(thread)


@patch("itsim.machine.process_management.process.Process")
def test_callback(mock_proc):
    sim = Simulator()
    thread = Thread(sim, mock_proc, 0)

    # This lambda actually runs, so it needs to accept the Thread argument
    thread.clone(lambda _: 0)
    sim.run()

    assert thread._scheduled == set()
    mock_proc.thread_complete.assert_called_with(thread)


@patch("itsim.machine.process_management.process.Process")
def test_callback_args(mock_proc):

    sim = Simulator()
    thread = Thread(sim, mock_proc, 0)

    class AdHocError(Exception):
        pass

    def f(dashboard, arg, kwarg):
        if isinstance(dashboard, Dashboard) and arg == 0 and kwarg == 1:
            raise AdHocError()

    thread.clone(f, 0, kwarg=1)
    with raises(AdHocError):
        sim.run()
