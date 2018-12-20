from itsim.software.context import Context
from itsim.machine.process_management.process import Process
from itsim.machine.process_management.thread import Thread, ThreadKilled
from itsim.simulator import Simulator, advance
from itsim.types import Timeout
from itsim.utils import assert_list

from pytest import fixture, raises, fail
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
        set() == thread._computations],
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
def test_run_in(mock_sim, proc):
    thread = Thread(mock_sim, proc, 0)
    t = 10

    (f_a, ccb_a) = thread.run_in(t, lambda: 0)
    mock_sim.add.assert_called_with(ccb_a, f_a, t)
    assert thread._computations == {f_a}

    (f_b, ccb_b) = thread.run_in(t, lambda: 1)
    mock_sim.add.assert_called_with(ccb_b, f_b, t)
    assert thread._computations == {f_a, f_b}


@patch("itsim.simulator.Simulator")
def test_run(mock_sim, proc):
    thread = Thread(mock_sim, proc, 0)

    (f_a, ccb_a) = thread.run(lambda: 0)
    mock_sim.add.assert_called_with(ccb_a, f_a, 0)
    assert thread._computations == {f_a}

    (f_b, ccb_b) = thread.run(lambda: 1)
    mock_sim.add.assert_called_with(ccb_b, f_b, 0)
    assert thread._computations == {f_a, f_b}


@patch("itsim.simulator.Simulator")
@patch("itsim.machine.process_management.process.Process")
def test_exit_f(mock_sim, mock_proc):
    thread = Thread(mock_sim, mock_proc, 0)

    (f_a, _) = thread.run(lambda: 0)
    thread.exit_f(f_a)
    assert thread._computations == set()
    mock_proc.thread_complete.assert_called_with(thread)


@patch("itsim.machine.process_management.process.Process")
def test_callback(mock_proc):
    sim = Simulator()
    thread = Thread(sim, mock_proc, 0)

    # This lambda actually runs, so it needs to accept the Thread argument
    thread.run(lambda _: 0)
    sim.run()

    assert thread._computations == set()
    mock_proc.thread_complete.assert_called_with(thread)


@patch("itsim.machine.process_management.process.Process")
def test_callback_args(mock_proc):

    sim = Simulator()
    thread = Thread(sim, mock_proc, 0)

    class AdHocError(Exception):
        pass

    def f(context, arg, kwarg):
        if isinstance(context, Context) and arg == 0 and kwarg == 1:
            raise AdHocError()

    thread.run(f, 0, kwarg=1)
    with raises(AdHocError):
        sim.run()


@patch("itsim.machine.process_management.process.Process")
def test_is_alive_cycle(mock_proc):
    DELAY = 20
    is_running = False

    def f(_):
        nonlocal is_running
        is_running = True
        advance(DELAY)

    sim = Simulator()
    thread = Thread(sim, mock_proc, 0)
    assert thread.is_alive()
    thread.run(f)
    assert thread.is_alive()
    sim.run(DELAY / 2)
    assert is_running
    assert thread.is_alive()
    sim.run()
    assert not thread.is_alive()


def run_test_join(delay, timeout, expected_log):
    with patch("itsim.machine.process_management.process.Process") as mock_proc:
        log = []

        def f(_, delay):
            advance(delay)

        def joiner(t):
            try:
                t.join(timeout)
                assert not t.is_alive()
                log.append("complete")
            except Timeout:
                log.append("timeout")
                assert t.is_alive()

        sim = Simulator()
        thread = Thread(sim, mock_proc, 0)
        thread.run(f, 20)
        sim.add(joiner, thread)
        sim.run()
        assert log == [expected_log]


def test_join_complete():
    run_test_join(10, 100, "complete")


def test_join_timeout():
    run_test_join(10, 5, "timeout")


def run_test_kill(delay_thread, delay_kill, delay_join, expect_alive_after_kill):
    with patch("itsim.machine.process_management.process.Process") as mock_proc:
        log = []

        def f(_):
            try:
                advance(delay_thread)
            except ThreadKilled:
                raise
            except Exception:
                fail("Ended by an exception distinct from ThreadKilled.")

        def joiner(t):
            advance(delay_join)
            t.join()
            assert not t.is_alive()
            log.append("joiner")

        def killer(t):
            advance(delay_kill)
            t.kill()
            assert t.is_alive() == expect_alive_after_kill
            log.append("killer")

        sim = Simulator()
        thread = Thread(sim, mock_proc, 0)
        thread.run(f)
        thread.run_in(delay_thread / 2, f)
        sim.add(joiner, thread)
        sim.add(killer, thread)
        sim.run()
        assert log == ["killer", "joiner"]


def test_kill_live_trigger_join():
    run_test_kill(100, 10, 0, True)


def test_kill_live_join_after():
    run_test_kill(100, 10, 30, True)


def test_kill_dead():
    run_test_kill(10, 20, 30, False)
