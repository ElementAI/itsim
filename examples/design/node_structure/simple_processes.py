from enum import Enum, unique

from greensim import now, advance

from itsim.it_objects import Simulator
from itsim.node import Node
from itsim.node.accounts import UserAccount, UserGroup
from itsim.node.files import File
from itsim.node.files.access_policies import Policy, TargetedPolicy
from itsim.node.processes.thread import Thread

from typing import Callable


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

    def ping(thread: Thread) -> None:
        proc = thread._process
        log("Howdy. It's %s O'clock" % now())
        log("\t I'm in process number %s" % proc._n)
        if proc._parent is not None:
            log("\t\t I'm a proud descendant of process %s" % proc._parent._n)
        log("\t\t I'm in thread  number %s" % thread._n)

        # Show off forking from withing a process
        proc.fork_exec(sim, short_kid)

        # This just fills the function set in the Thread object to show that it works and how it looks
        thread.clone(lambda _: advance(1))
        thread.clone(lambda _: advance(1))

    # Builder patter for a priori setup of functions running at specific times
    pm = Node().with_proc_at(sim, 1, ping)

    # Setting up a new process, forking it from outside, and setting up some concurrent threads
    proc = pm.fork_exec(sim, ping)
    kid = proc.fork_exec(sim, ping)
    kid.exc_in(sim, 1, ping)
    kid.exc_in(sim, 2, ping)
    kid.exc_in(sim, 3, ping)

    user: UserAccount = UserAccount("demo")
    group: UserGroup = UserGroup("demo")
    group.add_members(user)

    default_policy = TargetedPolicy(False, False, False)
    user_policy = TargetedPolicy(False, False, True)
    group_policy = TargetedPolicy(False, False, True)

    user_allowed: Policy = Policy(default_policy, user_rules={user: user_policy})
    group_allowed: Policy = Policy(default_policy, group_rules={group: group_policy})
    runnable_a: File[Callable[[Thread], None]] = File(ping, user_allowed)
    runnable_b: File[Callable[[Thread], None]] = File(ping, group_allowed)
    pm.run_file(sim, runnable_a, user)
    pm.run_file(sim, runnable_b, user)
    sim.run()


if __name__ == '__main__':
    run_sample()
