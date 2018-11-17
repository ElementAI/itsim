from .__init__ import _Link
from itsim.machine.node import Node
from itsim.machine.process_management import _Daemon
from itsim.simulator import Simulator
from itsim.types import PortRepr, Protocol


class Router(Node):
    """
    Node tasked with forwarding messages between LANs connected to it, and over to a WAN interface. The router is
    configured through links it forwards between, and thus is made to implement certain network services over the
    appropriate links.

    :param wan: WAN interface, articulated by a ``itsim.network.Link`` instance.
    :param lan: LAN links connected to this router.
    """

    def __init__(self) -> None:
        super().__init__()

    def with_daemon_on(self,
                       sim: Simulator,
                       link: _Link,
                       daemon: _Daemon,
                       protocol: Protocol,
                       *ports: PortRepr) -> "Router":
        self.connected_to(link)
        self.networking_daemon(sim, protocol, *ports)(daemon)
        return self
