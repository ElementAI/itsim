from greensim import now, Simulator
from greensim.random import constant, normal

from itsim.it_objects.endpoint import Endpoint
from itsim.network import Network

from pytest import raises


def test_name():
    net = Network(Simulator(),
                  cidr="192.168.4.0/24",
                  bandwidth=constant(1),
                  latency=normal(5, 1),
                  num_skip_addresses=100)
    assert Endpoint("Fin", net).name == "Fin"


def test_network():
    net = Network(Simulator(),
                  cidr="192.168.4.0/24",
                  bandwidth=constant(1),
                  latency=normal(5, 1),
                  num_skip_addresses=100)
    # NB Network does not implement __eq__ so this is comparing pointers
    assert Endpoint("Fin", net).network == net


def test_sim():
    net_sim = Simulator()
    net = Network(net_sim,
                  cidr="192.168.4.0/24",
                  bandwidth=constant(1),
                  latency=normal(5, 1),
                  num_skip_addresses=100)
    indie_sim = Simulator()
    # NB Simulator does not implement __eq__ so this is comparing pointers
    assert Endpoint("Fin", net).sim == net_sim
    assert Endpoint("Fin", net, indie_sim).sim == indie_sim


############################################################
# Define constants for the many tests of install(_in, _at) #
############################################################


flag = 0
sim = Simulator()
net = Network(sim,
              cidr="192.168.4.0/24",
              bandwidth=constant(1),
              latency=normal(5, 1),
              num_skip_addresses=100)
traveller = Endpoint("Ishmael", net)
secret = "Rumplestiltzkin"


##################################################################################
# Define functions that will be installed in the many tests of install(_in, _at) #
##################################################################################


def no_argument():
    pass


def single_argument(node):
    global flag
    flag = 1
    assert traveller == node


def multi_argument(node, signal):
    global flag, secret
    flag = 1
    assert traveller == node
    assert secret == signal


####################################################################################
# Helper functions to deal with simulations in the many tests of install(_in, _at) #
####################################################################################

# Vanilla install, just passes arguments through and checks that fn is run using flag
def run_install(sim, node, fn, *args, **kwargs):
    global flag
    flag = 0
    sim._clear()
    node.install(fn, *args, **kwargs)
    sim.run()
    assert flag == 1


# Wraps fn in another function that checks the delay happend and passes arguments through
def run_install_at(sim, node, fn, *args, **kwargs):
    global flag
    flag = 0
    delay = 10

    def time_check(*args, **kwargs):
        nonlocal delay, fn
        assert delay == now()
        fn(*args, **kwargs)

    sim._clear()
    node.install_at(delay, time_check, *args, **kwargs)
    sim.run()
    assert flag == 1


# Same as above, but runs the simulation first to make sure the relative functionality of _in is used
def run_install_in(sim, node, fn, *args, **kwargs):
    global flag
    flag = 0
    delay = 10

    def time_check(*args, **kwargs):
        nonlocal delay, fn
        assert 2 * delay == now()
        fn(*args, **kwargs)

    sim._clear()
    sim.run(delay)
    node.install_in(delay, time_check, *args, **kwargs)
    sim.run()
    assert flag == 1


#####################################################
# Testing all the permutations of install(_in, _at) #
#####################################################


def test_install_single():
    run_install(sim, traveller, single_argument)


def test_install_multi():
    run_install(sim, traveller, multi_argument, secret)


def test_install_kw():
    run_install(sim, traveller, multi_argument, signal=secret)


def test_install_no():
    traveller.install(no_argument)
    with raises(TypeError):
        sim.run()


def test_install_at_single():
    run_install_at(sim, traveller, single_argument)


def test_install_at_multi():
    run_install_at(sim, traveller, multi_argument, secret)


def test_install_at_kw():
    run_install_at(sim, traveller, multi_argument, signal=secret)


def test_install_at_no():
    traveller.install_at(10, no_argument)
    with raises(TypeError):
        sim.run()


def test_install_in_single():
    run_install_in(sim, traveller, single_argument)


def test_install_in_multi():
    run_install_in(sim, traveller, multi_argument, secret)


def test_install_in_kw():
    run_install_in(sim, traveller, multi_argument, signal=secret)


def test_install_in_no():
    traveller.install_in(10, no_argument)
    with raises(TypeError):
        sim.run()
