from itsim.internet.endpoint import Endpoint
from itsim.network.link import Link
from itsim.network.service.dhcp import DHCPDaemon
from itsim.simulator import Simulator
from itsim.types import Protocol


class Router(Endpoint):
    """
    Node tasked with forwarding messages between LANs connected to it, and over to a WAN interface. The router is
    configured through links it forwards between, and thus is made to implement certain network services over the
    appropriate links.

    :param wan: WAN interface, articulated by a ``itsim.network.Link`` instance.
    :param lan: LAN links connected to this router.
    """

    def __init__(self, wan: Link, *lan: Link) -> None:
        super().__init__()
        raise NotImplementedError()

    def install_dhcp(self, sim: Simulator):
        self.networking_daemon(sim, Protocol.UDP, 67)(DHCPDaemon)
