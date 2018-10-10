import weakref

from collections import OrderedDict
from typing import Any, MutableMapping

from greensim import advance
from greensim.random import VarRandom

from itsim import _Node
from itsim.it_objects.networking import _Link
from itsim.it_objects.packet import Packet
from itsim.types import Address, AddressRepr, as_address


class AddressError(Exception):

    def __init__(self, value: Any) -> None:
        super().__init__()
        self.value_for_address = value


class AddressInUse(AddressError):
    pass


class InvalidAddress(AddressError):
    pass


class Link(_Link):

    def __init__(self, bandwidth: VarRandom[float], latency: VarRandom[float]) -> None:
        super()
        self._bandwidth: VarRandom[float] = bandwidth
        self._latency: VarRandom[float] = latency
        self._nodes: MutableMapping[Address, weakref.ReferenceType[_Node]] = OrderedDict()

    def add_node(self, node: _Node, ar: AddressRepr) -> None:

        address = as_address(ar)

        if address in self._nodes:
            raise AddressInUse(address)

        self._nodes[address] = weakref.ref(node)

    def drop_node(self, ar: AddressRepr) -> bool:

        address = as_address(ar)

        if address in self._nodes:
            del self._nodes[address]
            return True

        return False

    def transmit(self, packet: Packet, sender: _Node) -> None:

        receivers = self._nodes.values()

        def transmission():
            advance(next(self._latency) + len(packet) / next(self._bandwidth))
            for node in receivers:
                self.sim.add(node._receive, packet)

        self.sim.add(transmission)
