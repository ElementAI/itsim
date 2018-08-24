from greensim import Simulator
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
    assert Endpoint("Rumplestiltzkin", net).name == "Rumplestiltzkin"


def test_network():
    net = Network(Simulator(),
                  cidr="192.168.4.0/24",
                  bandwidth=constant(1),
                  latency=normal(5, 1),
                  num_skip_addresses=100)
    # NB Network does not implement __eq__ so this is comparing pointers
    assert Endpoint("Rumplestiltzkin", net).network == net


def test_install_single_arg():
    sim = Simulator()
    net = Network(sim,
                  cidr="192.168.4.0/24",
                  bandwidth=constant(1),
                  latency=normal(5, 1),
                  num_skip_addresses=100)
    traveller = Endpoint("Ishmael", net)
    flag = 0

    def single_argument(node):
        nonlocal flag
        flag = 1
        assert node == traveller

    def run_install():
        traveller.install(single_argument)

    sim.add(run_install)
    sim.run()
    assert flag == 1


def test_install_multi_arg():
    sim = Simulator()
    net = Network(sim,
                  cidr="192.168.4.0/24",
                  bandwidth=constant(1),
                  latency=normal(5, 1),
                  num_skip_addresses=100)
    traveller = Endpoint("Ishmael", net)
    flag = 0
    secret = "Rumplestiltzkin"

    def multi_argument(signal, node):
        nonlocal flag, secret
        flag = 1
        assert node == traveller
        assert signal == secret

    def run_install():
        nonlocal secret
        traveller.install(multi_argument, secret)

    sim.add(run_install)
    sim.run()
    assert flag == 1


def test_not_enough_args():
    sim = Simulator()
    net = Network(sim,
                  cidr="192.168.4.0/24",
                  bandwidth=constant(1),
                  latency=normal(5, 1),
                  num_skip_addresses=100)
    traveller = Endpoint("Ishmael", net)

    def no_argument():
        pass

    def run_install():
        traveller.install(no_argument)

    sim.add(run_install)
    with raises(TypeError):
        sim.run()
