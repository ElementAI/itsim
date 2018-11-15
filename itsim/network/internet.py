from itsim.simulator import Simulator
from itsim.machine import _Node
from itsim.network.link import Link
from itsim.random import VarRandomSize, VarRandomTime, VarRandomBandwidth
from itsim.types import HostnameRepr, Protocol


class Host(_Node):
    """
    Internet-facing node that provides various application services. This is a lightweight ``Host`` instance, for which
    no internal visibility is granted throughout the simulation.

    Note that anywhere a *simulator* instance is referred to, the class in question is fully qualified as
    ``itsim.simulator.Simulator``. Such a simulator instance must be provided over each service or daemon instantiation
    in order to articulate and render the discrete event sequence of that service.
    """

    def __init__(self) -> None:
        super().__init__()

    def dns(self, sim: Simulator, frequency: float = 1) -> "Host":
        """
        Makes the node run a DNS service over UDP port 53.
        """
        raise NotImplementedError()
        return self

    def web_server(
        self,
        sim: Simulator,
        len_response: VarRandomSize,
        protocol: Protocol = Protocol.ANY,
        frequency: float = 1
    ) -> "Host":
        """
        Makes the node run a web server over common HTTP ports, in a request/reply paradigm (one logical request packet,
        one logical reply packet).

        :param sim: Simulator instance.
        :param len_response: Random number sequence corresponding to the length in bytes of the response to each
            request.
        :param protocol: Protocols over which the service is provided. Value ``Protocol.CLEAR`` indicates cleartext HTTP
            service over port 80; value ``Protocol.SSL`` indicates crypted HTTPS service over port 443. By default, both
            are provided.
        :param frequency: Relative frequency of requests sent over each serviced port, assuming other types of service
            besides one-shot request/reply embodied by this service. For instance, if streaming service is also provided
            over HTTPS, with a frequency 2, while frequency 1 is selected for the request/reply server, then requests to
            port 443 are will be randomly sampled so that they are considered to be streaming requests (and deserved
            accordingly) twice as much as request/reply requests.

        :return: The host itself, to facilitate building up the instance.
        """
        raise NotImplementedError()
        return self

    def web_streaming(
        self,
        sim: Simulator,
        bandwidth_usage: VarRandomBandwidth,
        duration: VarRandomTime,
        protocol: Protocol = Protocol.SSL,
        frequency: float = 1
    ) -> "Host":
        """
        Makes the node run a web server over common HTTP ports, in a streaming paradigm (one logical request packet,
        followed by a sequence of logical reply packets).

        :param sim: Simulator instance.
        :param bandwidth_usage: While replying, the server will generate packets so as to use bandwidth in accordance
            with numbers gotten from this random number generator.
        :param duration: Duration of the stream reply is taken from this random number generator.
        :param protocol: Protocols over which the service is provided. Value ``Protocol.CLEAR`` indicates cleartext HTTP
            service over port 80; value ``Protocol.SSL`` indicates crypted HTTPS service over port 443. By default,
            streaming is provided only over HTTPS.
        :param frequency: Relative frequency of requests sent over each serviced port, assuming other types of service
            besides one-shot request/reply embodied by this service. For instance, if streaming service is also provided
            over HTTPS, with a frequency 2, while frequency 1 is selected for the request/reply server, then requests to
            port 443 are will be randomly sampled so that they are considered to be streaming requests (and deserved
            accordingly) twice as much as request/reply requests.

        :return: The host itself, to facilitate building up the instance.
        """
        raise NotImplementedError()
        return self

    def websocket(
        self,
        sim: Simulator,
        duration: VarRandomTime,
        request_interval: VarRandomTime,
        update_interval: VarRandomTime,
        len_beacon: VarRandomSize
    ) -> "Host":
        """
        Makes the node run a websocket session from a connection initiated through a request/reply ``web_server``. The
        paradigm is that the client periodically sends new *request* packets over the same socket connection, which get
        immediate 1-packet replies; in addition, the server sends unsollicited *update* packets over the connection.

        :param sim: Simulator instance.
        :param duration: Duration of the websocket session is taken from this random number generator. After that, the
            connection with the client is closed.
        :param request_interval: Interval suggested to the client to wait between sending websocket requests, as a
            number generator.
        :param update_interval: The wait times between updates are taken from this random generator.
        :param len_beacon: The length of each sent packet (whether as a reply to a request or as an update) is taken
            from this random generator.

        :return: The host itself, to facilitate building up the instance.
        """
        raise NotImplementedError()
        return self

    def shell_server(
        self,
        sim: Simulator,
        duration: VarRandomTime,
        interval: VarRandomTime,
        request: VarRandomSize,
        response: VarRandomSize
    ) -> "Host":
        """
        Makes the node run a secure shell server (SSH). The service paradigm is a sequence of requests and responses,
        over a single connection. The service is provided over port 22.

        :param sim: Simulator instance.
        :param duration: Duration of the shell session is taken from this random generator.
        :param interval: Time interval between requests, which is suggested to the client, is taken from this random
            number generator.
        :param request: Length (in bytes) of requests is taken from this random generator.
        :param response: Length (in bytes) of responses is taken from this random generator.

        :return: The host itself, to facilitate building up the instance.
        """
        raise NotImplementedError()
        return self


class Internet(Link):
    """
    Global environment outside of any local network, where arbitrary nodes are set up with varying physical transport
    properties. The local networks are connected to this environment through routers.
    """

    def __init__(self) -> None:
        raise NotImplementedError()

    def host(self, hostname: HostnameRepr, latency: VarRandomTime, bandwidth: VarRandomBandwidth) -> Host:
        """
        Instantiates a new host connected to the Internet. This returns the new host instance so it may be set up with
        various services.

        :param hostname: Hostname by which the host can be reached.
        :param latency: Latency to connect to this host (putatively from an ad hoc local network).
        :param bandwidth: Bandwidth availed when connecting to this host.

        :return: A new host instance, so it can be built up with various services.
        """
        raise NotImplementedError()
