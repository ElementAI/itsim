from typing import Any, Callable, Optional

from greensim import Simulator

from itsim.network import Network
from itsim.node import Node


class Endpoint(Node):

    def __init__(self, name: str, network: Network, sim: Optional[Simulator] = None) -> None:
        super().__init__()
        self._name = name
        self._network = network
        if sim is None:
            self._sim = network.sim
        else:
            self._sim = sim

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
