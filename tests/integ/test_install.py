from greensim import GREENSIM_TAG_ATTRIBUTE, now, Process, Simulator, tagged
from greensim.random import constant, normal
from greensim.tags import Tags

from itsim.it_objects.endpoint import Endpoint
from itsim.network import Network

from pytest import fixture

#########################################################################
# Define constants and fixtures for the many tests of install(_in, _at) #
#########################################################################


class IntegTestTag(Tags):
    ALICE = 0
    BOB = ""
    CANADA = {}


ENDPOINT_PROPERTY = "test_calling_endpoint"
FLAG_PROPERTY = "test_flag"
SHORT_TAG_SET = set([IntegTestTag.ALICE, IntegTestTag.BOB])


@fixture
def simulator():
    return Simulator()


@fixture
def network(simulator):
    return Network(simulator,
                   cidr="192.168.4.0/24",
                   bandwidth=constant(1),
                   latency=normal(5, 1),
                   num_skip_addresses=100)


@fixture
def endpoint(network):
    return Endpoint("Traveller", network)


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
def run_install(sim, end, fn, *args, **kwargs):
    setattr(sim, ENDPOINT_PROPERTY, end)
    setattr(sim, FLAG_PROPERTY, 0)
    end.install(fn, *args, **kwargs)
    sim.run()
    assert 1 == getattr(sim, FLAG_PROPERTY)


# Wraps fn in another function that checks the delay happend and passes arguments through
def run_install_at(sim, end, fn, *args, **kwargs):
    delay = 10

    def time_check(*args, **kwargs):
        assert delay == now()
        fn(*args, **kwargs)

    setattr(sim, ENDPOINT_PROPERTY, end)
    setattr(sim, FLAG_PROPERTY, 0)
    end.install_at(delay, create_time_check(delay, fn), *args, **kwargs)
    sim.run()
    assert 1 == getattr(sim, FLAG_PROPERTY)


# Same as above, but runs the simulation first to make sure the relative functionality of _in is used
def run_install_in(sim, end, fn, *args, **kwargs):
    delay = 10

    def time_check(*args, **kwargs):
        assert 2 * delay == now()
        fn(*args, **kwargs)

    setattr(sim, ENDPOINT_PROPERTY, end)
    setattr(sim, FLAG_PROPERTY, 0)
    sim.run(delay)
    end.install_in(delay, create_time_check(2 * delay, fn), *args, **kwargs)
    sim.run()
    assert 1 == getattr(sim, FLAG_PROPERTY)


@tagged(*SHORT_TAG_SET)
def tag_checker(node, tag_set):
    setattr(Process.current().rsim(), FLAG_PROPERTY, 1)
    assert tag_set == Process.current()._tag_set


def test_install_tags(endpoint):
    run_install(endpoint.sim, endpoint, tag_checker, SHORT_TAG_SET)


def test_install_at_tags(endpoint):
    run_install_at(endpoint.sim, endpoint, tag_checker, SHORT_TAG_SET)


def test_install_in_tags(endpoint):
    run_install_in(endpoint.sim, endpoint, tag_checker, SHORT_TAG_SET)


# As defined in the __init__ method of Process, a new Process should take tags from
# the function it is passed, as well as the currently running Process
# These test that install shows consistent behavior


def test_install_propogate(endpoint):

    @tagged(IntegTestTag.CANADA)
    def tag_propogator(node, tag_set):
        node.install(tag_checker, tag_set | set([IntegTestTag.CANADA]))

    run_install(endpoint.sim, endpoint, tag_propogator, SHORT_TAG_SET)


def test_install_at_propogate(endpoint):

    @tagged(IntegTestTag.CANADA)
    def tag_propogator(node, tag_set):
        node.install_at(now() + 10, create_time_check(now() + 10, tag_checker), tag_set | set([IntegTestTag.CANADA]))

    run_install_at(endpoint.sim, endpoint, tag_propogator, SHORT_TAG_SET)


def test_install_in_propogate(endpoint):

    @tagged(IntegTestTag.CANADA)
    def tag_propogator(node, tag_set):
        node.install_in(10, create_time_check(now() + 10, tag_checker), tag_set | set([IntegTestTag.CANADA]))

    run_install_in(endpoint.sim, endpoint, tag_propogator, SHORT_TAG_SET)
