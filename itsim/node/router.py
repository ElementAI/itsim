from itsim.network import Link
from itsim.node import Node


class Router(Node):

    def __init__(self, wan: Link, *lan: Link) -> None:
        super().__init__()
        raise NotImplementedError()
