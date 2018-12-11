from itsim.machine.dashboard import Dashboard
from itsim.machine.node import Node
from itsim.machine.process_management.process import Process
from itsim.machine.process_management.thread import Thread
from itsim.simulator import Simulator, advance
from itsim.types import Timeout
from itsim.utils import assert_list

from pytest import fixture
from unittest.mock import patch


@fixture
@patch("itsim.machine.node.Node")
def proc_a(mock_node):
    return Process(0, mock_node)


@fixture
@patch("itsim.machine.node.Node")
def proc_b(mock_node):
    return Process(1, mock_node)


@fixture
@patch("itsim.machine.process_management.process.Process")
def thread(mock_proc):
    return Thread(Simulator(), mock_proc, 0)


@patch("itsim.machine.node.Node")
def test_init(mock_node):
    n = 0
    parent = Process(n, mock_node)
    proc = Process(n, mock_node, parent)
    assert_list([
        set() == proc._children,
        parent == proc._parent,
        set() == proc._threads,
        n == proc._n,
        mock_node == proc._node,
        0 == proc._thread_counter],
        throw=True)


@patch("itsim.machine.node.Node")
def test_eq(mock_node, proc_a, proc_b):
    assert proc_a == proc_a

    n = 0
    assert Process(n, mock_node, proc_a) == Process(n, mock_node, proc_a)

    assert_list([
        Process(n, mock_node, proc_a) != Process(1, mock_node, proc_a),
        Process(n, mock_node, proc_a) != Process(n, Node(), proc_a)],
        throw=True)


@patch("itsim.machine.node.Node")
def test_hash(mock_node, proc_a, proc_b):
    assert hash(proc_a) == hash(proc_a)

    n = 0
    assert hash(Process(n, mock_node, proc_a)) == hash(Process(n, mock_node, proc_a))

    assert_list([
        hash(Process(n, mock_node, proc_a)) != hash(Process(1, mock_node, proc_a)),
        hash(Process(n, mock_node, proc_a)) != hash(Process(n, Node(), proc_a))],
        throw=True)


@patch("itsim.simulator.Simulator")
def test_exc_in(mock_sim, proc_a):
    time = 10

    t_a = proc_a.exc_in(mock_sim, time, lambda: 0)

    assert set([t_a]) == proc_a._threads
    assert 1 == proc_a._thread_counter

    t_b = proc_a.exc_in(mock_sim, time, lambda: 0)
    assert set([t_a, t_b]) == proc_a._threads
    assert 2 == proc_a._thread_counter


@patch("itsim.simulator.Simulator")
def test_exc(mock_sim, proc_a):
    t_a = proc_a.exc(mock_sim, lambda: 0)
    assert set([t_a]) == proc_a._threads
    assert 1 == proc_a._thread_counter

    t_b = proc_a.exc(mock_sim, lambda: 0)
    assert set([t_a, t_b]) == proc_a._threads
    assert 2 == proc_a._thread_counter


@patch("itsim.simulator.Simulator")
@patch("itsim.machine.node.Node")
@patch("itsim.machine.process_management.process.Process")
def test_thread_complete(mock_sim, mock_node, mock_proc):
    proc = Process(0, mock_node, mock_proc)
    t_a = proc.exc(mock_sim, lambda: 0)

    proc.thread_complete(t_a)
    assert set([]) == proc._threads
    assert 1 == proc._thread_counter
    mock_proc.child_complete.assert_called_with(proc)
    mock_node.proc_exit.assert_called_with(proc)


@patch("itsim.machine.node.Node")
def test_parent_child_relationship(mock_node):
    parent = Process(0, mock_node)
    kid = Process(1, mock_node, parent)
    assert parent._parent is None
    assert kid._parent is parent
    assert parent._children == {kid}
    assert len(kid._children) == 0


@patch("itsim.machine.node.Node")
def test_child_complete(mock_node):
    parent = Process(0, mock_node)
    kid = Process(1, mock_node, parent)
    parent.child_complete(kid)
    assert set() == parent._children


def run_process_wait_test(timeout, expected, has_thread = True, delay_before_wait = 0):
    with patch("itsim.machine.node.Node") as mock_node:
        def thread_behaviour(dashboard: Dashboard):
            advance(10)

        sim = Simulator()
        proc = Process(1234, mock_node)
        if has_thread:
            proc.exc(sim, thread_behaviour)
        log = []

        def wait_for_proc():
            advance(delay_before_wait)
            try:
                proc.wait(timeout)
                log.append("complete")
            except Timeout:
                log.append("timeout")

        sim.add(wait_for_proc)
        sim.run()

        assert log == [expected]


def test_process_wait_no_more_thread():
    run_process_wait_test(None, "complete", True, 20)


def test_process_wait_complete_no_timeout():
    run_process_wait_test(None, "complete")


def test_process_wait_complete_with_timeout():
    run_process_wait_test(20, "complete")


def test_process_wait_timeout():
    run_process_wait_test(5, "timeout")


def test_process_wait_no_thread_not_started():
    run_process_wait_test(100, "timeout", False)
