from greensim import GREENSIM_TAG_ATTRIBUTE, now, Process, Simulator, tagged
from greensim.random import constant, normal
from greensim.tags import Tags

from itsim.it_objects.endpoint import Endpoint
from itsim.network import Network

############################################################
# Define constants for the many tests of install(_in, _at) #
############################################################


class IntegTestTag(Tags):
    ALICE = 0
    BOB = ""
    CANADA = {}


flag = 0
sim = Simulator()
net = Network(sim,
              cidr="192.168.4.0/24",
              bandwidth=constant(1),
              latency=normal(5, 1),
              num_skip_addresses=100)
traveller = Endpoint("Ishmael", net)


####################################################################################
# Helper functions to deal with simulations in the many tests of install(_in, _at) #
####################################################################################


# Wraps an arbitrary function in order to check that it is being called at the right time
# The returned function takes the tags of the argument function
def create_time_check(delay, fn):
    def time_check(*args, **kwargs):
        nonlocal delay, fn
        assert delay == now()
        fn(*args, **kwargs)

    # NB this is discouraged in Production code. Tags should be applied at the top level,
    # where they can be propogated down. This is just to keep the test helper generic
    if hasattr(fn, GREENSIM_TAG_ATTRIBUTE):
        time_check = tagged(*getattr(fn, GREENSIM_TAG_ATTRIBUTE))(time_check)

    return time_check


# Vanilla install, just passes arguments through and checks that fn is run using flag
def run_install(sim, node, fn, *args, **kwargs):
    global flag
    flag = 0
    sim._clear()
    node.install(fn, *args, **kwargs)
    sim.run()
    assert flag == 1


# Wraps fn in another function that checks the delay happened and passes arguments and tags through
def run_install_at(sim, node, fn, *args, **kwargs):
    global flag
    flag = 0
    delay = 10

    sim._clear()
    node.install_at(delay, create_time_check(delay, fn), *args, **kwargs)
    sim.run()
    assert flag == 1


# Same as above, but runs the simulation first to make sure the relative functionality of _in is used
def run_install_in(sim, node, fn, *args, **kwargs):
    global flag
    flag = 0
    delay = 10

    sim._clear()
    sim.run(delay)
    node.install_in(delay, create_time_check(2 * delay, fn), *args, **kwargs)
    sim.run()
    assert flag == 1


short_tag_set = set([IntegTestTag.ALICE, IntegTestTag.BOB])


@tagged(*short_tag_set)
def tag_checker(node, tag_set):
    global flag
    flag = 1
    assert tag_set == Process.current()._tag_set


def test_install_tags():
    run_install(sim, traveller, tag_checker, short_tag_set)


def test_install_at_tags():
    run_install_at(sim, traveller, tag_checker, short_tag_set)


def test_install_in_tags():
    run_install_in(sim, traveller, tag_checker, short_tag_set)


# As defined in the __init__ method of Process, a new Process should take tags from
# the function it is passed, as well as the currently running Process
# These test that install shows consistent behavior


def test_install_propogate():

    @tagged(IntegTestTag.CANADA)
    def tag_propogator(node, tag_set):
        node.install(tag_checker, tag_set | set([IntegTestTag.CANADA]))

    run_install(sim, traveller, tag_propogator, short_tag_set)


def test_install_at_propogate():

    @tagged(IntegTestTag.CANADA)
    def tag_propogator(node, tag_set):
        node.install_at(now() + 10, create_time_check(now() + 10, tag_checker), tag_set | set([IntegTestTag.CANADA]))

    run_install_at(sim, traveller, tag_propogator, short_tag_set)


def test_install_in_propogate():

    @tagged(IntegTestTag.CANADA)
    def tag_propogator(node, tag_set):
        node.install_in(10, create_time_check(now() + 10, tag_checker), tag_set | set([IntegTestTag.CANADA]))

    run_install_in(sim, traveller, tag_propogator, short_tag_set)
