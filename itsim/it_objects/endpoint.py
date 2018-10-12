from typing import Any, Callable

from itsim.it_objects import Simulator
from itsim.network import Network
from itsim.node import Node
from itsim.types import AddressRepr, CidrRepr


class Endpoint(Node):

    def __init__(self, name: str, network: Network, ar: AddressRepr = None, *forward_to: CidrRepr) -> None:
        super().__init__()
        self._name = name
        self._network = network
        self._sim = network.sim
        self.link_to(network, ar, *forward_to)

    @property
    def network(self) -> Network:
        return self._network

    @property
    def name(self) -> str:
        return self._name

    @property
    def sim(self) -> Simulator:
        return self._sim

    def install(self, fn_software: Callable, *args: Any, **kwargs: Any) -> None:
        self._sim.add(fn_software, self, *args, **kwargs)

    def install_in(self, delay: float, fn_software: Callable, *args: Any, **kwargs: Any) -> None:
        self._sim.add_in(delay, fn_software, self, *args, **kwargs)

    def install_at(self, moment: float, fn_software: Callable, *args: Any, **kwargs: Any) -> None:
        self._sim.add_at(moment, fn_software, self, *args, **kwargs)
