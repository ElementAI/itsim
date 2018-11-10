from collections import OrderedDict

from ipaddress import ip_address

from itsim.machine.node import Node
from itsim.machine.process_management.process import Process
from itsim.utils import assert_list


def test_init():
    node = Node()

    assert_list([
        node._address_default is None,
        OrderedDict() == node._sockets,
        OrderedDict() == node._links,
        set() == node._proc_set,
        0 == node._process_counter,
        Process(-1, node) == node._default_process_parent,
        OrderedDict() == node._port_table],
        throw=True)


def test_eq():
    node = Node()
    assert node == node

    assert Node() == Node()

    node._address_default = ip_address("0.0.0.0")
    assert node != Node()


def test_hash():
    node = Node()
    assert hash(node) == hash(node)

    assert hash(Node()) == hash(Node())

    node._address_default = ip_address("0.0.0.0")
    assert hash(node) != hash(Node())    
