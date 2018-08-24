from typing import Any, Callable

from greensim import Process

from itsim.network import Network
from itsim.node import Node


class Endpoint(Node):

    def __init__(self, name: str, network: Network) -> None:
        super().__init__()
        self._name = name
        self._network = network

    @property
    def network(self) -> Network:
        return self._network

    @property
    def name(self) -> str:
        return self._name

    def install(self, fn_software: Callable, *args: Any, **kwargs: Any) -> None:
        Process.current().rsim().add(fn_software, *args + (self,), **kwargs)
