from typing import Optional, Callable

from itsim.it_objects import ITObject
from itsim.link import Link
from itsim.node import Host
from itsim.random import VarRandomSize, VarRandomTime, VarRandomBandwidth
from itsim.simulator import Simulator
from itsim.types import HostnameRepr, Protocol, PortsRepr


class InternetHost(Host):

    def __init__(self) -> None:
        raise NotImplementedError()

    def dns(self, sim: Simulator, frequency: float = 1) -> "InternetHost":
        raise NotImplementedError()
        return self

    def web_server(
        self,
        sim: Simulator,
        len_response: VarRandomSize,
        protocol: Protocol = Protocol.ANY,
        frequency: float = 1
    ) -> "InternetHost":
        raise NotImplementedError()
        return self

    def web_streaming(
        self,
        sim: Simulator,
        bandwidth_usage: VarRandomBandwidth,
        duration: VarRandomTime,
        protocol: Protocol = Protocol.SSL,
        frequency: float = 1
    ) -> "InternetHost":
        raise NotImplementedError()
        return self

    def websocket(
        self,
        sim: Simulator,
        duration: VarRandomTime,
        request_interval: VarRandomTime,
        update_interval: VarRandomTime,
        len_beacon: VarRandomSize
    ) -> "InternetHost":
        raise NotImplementedError()
        return self

    def shell_server(
        self,
        sim: Simulator,
        duration: VarRandomTime,
        interval: VarRandomTime,
        request: VarRandomSize,
        response: VarRandomSize,
        frequency: float = 1
    ) -> "InternetHost":
        raise NotImplementedError()
        return self

    def daemon(
        self,
        sim: Simulator,
        tcp: Optional[PortsRepr] = None,
        udp: Optional[PortsRepr] = None,
        frequency: float = 1
    ) -> Callable:
        raise NotImplementedError()


class Internet(Link):
    """
    Global environment outside of any local network, where arbitrary nodes are set up with varying physical transport
    properties. The local networks are connected to this environment through routers.
    """

    def __init__(self) -> None:
        raise NotImplementedError()

    def host(self, hostname: HostnameRepr, latency: VarRandomTime, bandwidth: VarRandomBandwidth) -> InternetHost:
        raise NotImplementedError()


class Daemon(ITObject):
    pass
