from collections import OrderedDict
from ipaddress import _BaseAddress
from itertools import dropwhile
from numbers import Real
from typing import cast, Any, MutableMapping, List, Iterable, Iterator, Optional, Callable

from greensim import Simulator, advance
from greensim.random import VarRandom, bounded, expo

from itsim import MS, S, MbPS, CidrRepr, Cidr, as_cidr, Address, AddressRepr, as_address, Packet, _Node, Location


class AddressError(Exception):

    def __init__(self, value: Any) -> None:
        super().__init__()
        self.value_for_address = value


class InvalidAddress(AddressError):
    pass


class AddressInUse(AddressError):
    pass


class NetworkFull(Exception):
    pass


class CannotForward(AddressError):
    pass


class Network(object):

    def __init__(
        self,
        sim: Simulator,
        cidr: CidrRepr,
        latency: VarRandom[Real],
        bandwidth: VarRandom[Real],
        num_skip_addresses: int = 0
    ) -> None:
        super().__init__()
        self._sim = sim
        self._cidr = as_cidr(cidr)
        self._latency = bounded(latency, lower=0)
        self._bandwidth = bounded(bandwidth, lower=0.125)  # 1 bit / s  X-O
        self._nodes: MutableMapping[Address, _Node] = OrderedDict()
        self._forwarders: MutableMapping[Cidr, _Node] = OrderedDict()
        self._addresses_free: List[Address] = []
        self._top_free: Iterator[Address] = (
            addr
            for _, addr in dropwhile(
                lambda p: p[0] < num_skip_addresses,
                enumerate(self.cidr.hosts())
            )
        )

    @property
    def cidr(self) -> Cidr:
        return self._cidr

    @property
    def sim(self) -> Simulator:
        return self._sim

    def link(self, node: _Node, ar: AddressRepr = None, *forward_to: CidrRepr) -> Address:
        if ar is None:
            address = self._get_address_free()
        else:
            address = as_address(ar)

        if address not in self._cidr:
            raise InvalidAddress(address)
        if address in self._nodes:
            raise AddressInUse(address)

        self._nodes[address] = node
        if forward_to is not None:
            for cidr in (as_cidr(c) for c in forward_to):
                self._forwarders[cidr] = node

        return address

    def unlink(self, ar: AddressRepr) -> None:
        address = as_address(ar)
        if address in self._nodes:
            for cidr, node in self._forwarders.items():
                if address in node.addresses:
                    del self._forwarders[cidr]
            self._nodes[address].unlink_from(address)
            del self._nodes[address]
            self._addresses_free.append(address)

    def _get_address_free(self) -> Address:
        try:
            return cast(Address, next(self._top_free))
        except StopIteration:
            if len(self._addresses_free) > 0:
                address = self._addresses_free[0]
                del self._addresses_free[0]
                return address
            else:
                raise NetworkFull()

    @property
    def address_broadcast(self):
        return self._cidr.broadcast_address

    def transmit(self, packet: Packet, receiver_maybe: Optional[_Node] = None) -> None:
        if not isinstance(packet.dest.host, _BaseAddress):
            raise InvalidAddress(packet.dest.host)

        receivers: Iterable[_Node]
        if receiver_maybe is not None:
            receivers = [cast(_Node, receiver_maybe)]
        if packet.dest.host == self.address_broadcast:
            receivers = self._nodes.values()
        elif packet.dest.host in self._nodes:
            receivers = [self._nodes[packet.dest.host]]
        else:
            receivers = [self._get_forwarder(cast(Address, packet.dest.host))]

        def transmission():
            advance(next(self._latency) + len(packet) / next(self._bandwidth))
            for node in receivers:
                node.receive(packet)
        self.sim.add(transmission)

    def _get_forwarder(self, dest: Address) -> _Node:
        candidates = [(cidr, node) for cidr, node in self._forwarders.items() if dest in cidr]
        if len(candidates) == 0:
            raise CannotForward(dest)
        return max(candidates, key=lambda cidr_node: cidr_node[0])[1]


class Internet(Network):

    def __init__(
        self,
        sim: Simulator,
        latency: Optional[VarRandom[Real]] = None,
        bandwidth: Optional[VarRandom[Real]] = None
    ) -> None:
        super().__init__(
            sim,
            cidr="0.0.0.0/0",
            latency=latency or bounded(expo(1 * S), lower=20 * MS),
            bandwidth=bandwidth or expo(10 * MbPS)
        )

    def add_receiver(self, loc: Location, receiver: Callable[[Packet], None]) -> None:
        raise NotImplementedError("Stub")
