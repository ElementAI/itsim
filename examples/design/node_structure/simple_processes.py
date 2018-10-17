from abc import ABC, abstractmethod

from enum import Enum, unique

from greensim import now, advance

from itsim.it_objects import ITObject, Simulator
from itsim.node import Node
from itsim.node.processes.process import Process
from itsim.node.processes.thread import Thread

from typing import Callable, Optional, Set


@unique
class Colors(Enum):
    RED = '\033[31m'
    GREEN = '\033[32m'
    YELLOW = '\033[33m'
    CLOSE = '\033[0m'


def log(msg: str, color: Colors = None) -> None:
    if color is not None:
        msg = color.value + msg + Colors.CLOSE.value
    print(msg)


def run_sample() -> None:
    sim = Simulator()

    # Simple output for the child processes
    def short_kid(t: Thread):
        advance(10)
        log("I'm a child process! #%s > #%s" % (t._process._parent._n, t._process._n), Colors.YELLOW)

    # The optional argument just proves type checking works for the Process and Thread even with extra args
    def ping(thread: Thread, optional: object = None) -> None:
        proc = thread._process
        log("Howdy. It's %s O'clock" % now())
        log("\t I'm in process number %s" % proc._n)
        if proc._parent is not None:
            log("\t\t I'm a proud descendant of process %s" % proc._parent._n)
        log("\t\t I'm in thread  number %s" % thread._n)

        # Show off forking from withing a process
        proc.fork_exc(sim, short_kid)

        # This just fills the function set in the Thread object to show that it works and how it looks
        thread.clone(lambda _: advance(1))
        thread.clone(lambda _: advance(1))

    # Builder patter for a priori setup of functions running at specific times
    pm = Node().with_proc_at(sim, 1, ping)

    # Setting up a new process, forking it from outside, and setting up some concurrent threads
    proc = pm.fork_exc(sim, ping)
    kid = proc.fork_exc(sim, ping)
    kid.exc_in(sim, 1, ping)
    kid.exc_in(sim, 2, ping)
    kid.exc_in(sim, 3, ping)
    sim.run()


if __name__ == '__main__':
    run_sample()
