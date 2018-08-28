from greensim import now, Process, Simulator
from greensim.random import constant, normal

from itsim.it_objects.endpoint import Endpoint
from itsim.network import Network
from itsim.types import as_address

from pytest import raises, fixture

from unittest.mock import patch


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


def test_name(network):
    assert Endpoint("Fin", network).name == "Fin"


def test_sim(simulator, network):
    # NB Simulator does not implement __eq__ so this is comparing pointers
    assert Endpoint("Fin", network).sim == network.sim


def test_link(network):
    addr = as_address("192.168.4.0")
    end = Endpoint("Fin", network, addr)
    assert end._networks[addr].address == addr
    assert end._networks[addr].network == network


@patch("itsim.network.Network")
def test_link_args(mock_net):
    cidrs = ("192.168.0.0/8", "192.168.1.0/8")
    addr = as_address("192.168.4.0")
    end = Endpoint("Fin", mock_net, addr, *cidrs)
    mock_net.link.assert_called_with(end, addr, *cidrs)


############################################################
# Define constants for the many tests of install(_in, _at) #
############################################################


SECRET = "Rumplestiltzkin"
ENDPOINT_PROPERTY = "test_calling_endpoint"
FLAG_PROPERTY = "test_flag"


##################################################################################
# Define functions that will be installed in the many tests of install(_in, _at) #
##################################################################################


def no_argument():
    pass


def single_argument(node):
    setattr(Process.current().rsim(), FLAG_PROPERTY, 1)
    assert getattr(Process.current().rsim(), ENDPOINT_PROPERTY) == node


def multi_argument(node, signal):
    setattr(Process.current().rsim(), FLAG_PROPERTY, 1)
    assert getattr(Process.current().rsim(), ENDPOINT_PROPERTY) == node
    assert SECRET == signal


####################################################################################
# Helper functions to deal with simulations in the many tests of install(_in, _at) #
####################################################################################

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
    end.install_at(delay, time_check, *args, **kwargs)
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
    end.install_in(delay, time_check, *args, **kwargs)
    sim.run()
    assert 1 == getattr(sim, FLAG_PROPERTY)


#####################################################
# Testing all the permutations of install(_in, _at) #
#####################################################


def test_install_single(endpoint):
    run_install(endpoint.sim, endpoint, single_argument)


def test_install_multi(endpoint):
    run_install(endpoint.sim, endpoint, multi_argument, SECRET)


def test_install_kw(endpoint):
    run_install(endpoint.sim, endpoint, multi_argument, signal=SECRET)


def test_install_no(endpoint):
    endpoint.install(no_argument)
    with raises(TypeError):
        endpoint.sim.run()


def test_install_at_single(endpoint):
    run_install_at(endpoint.sim, endpoint, single_argument)


def test_install_at_multi(endpoint):
    run_install_at(endpoint.sim, endpoint, multi_argument, SECRET)


def test_install_at_kw(endpoint):
    run_install_at(endpoint.sim, endpoint, multi_argument, signal=SECRET)


def test_install_at_no(endpoint):
    endpoint.install_at(10, no_argument)
    with raises(TypeError):
        endpoint.sim.run()


def test_install_in_single(endpoint):
    run_install_in(endpoint.sim, endpoint, single_argument)


def test_install_in_multi(endpoint):
    run_install_in(endpoint.sim, endpoint, multi_argument, SECRET)


def test_install_in_kw(endpoint):
    run_install_in(endpoint.sim, endpoint, multi_argument, signal=SECRET)


def test_install_in_no(endpoint):
    endpoint.install_in(10, no_argument)
    with raises(TypeError):
        endpoint.sim.run()
