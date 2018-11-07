from typing import MutableMapping

from greensim.random import expo, normal, bounded, linear, uniform

from itsim.network.internet import Internet, Daemon
from itsim.network.location import Location
from itsim.network.payload import Payload, PayloadDictionaryType
from itsim.node import Socket
from itsim.random import num_bytes
from itsim.simulator import Simulator
from itsim.types import Protocol
from itsim.units import B, KB, KbPS, MbPS, MIN, S, MS


sim = Simulator()
internet = Internet()


for address in ["8.8.8.8", "8.8.4.4"]:
    internet.host(
        address,
        latency=normal(10 * MS, 5 * MS),
        bandwidth=bounded(expo(10 * MbPS), lower=1 * MbPS)
    ).dns(sim)

for domain in ["newyorker.com", "amazon.com"]:
    internet.host(
        domain,
        latency=normal(10 * MS, 20 * MS),
        bandwidth=bounded(expo(10 * MbPS), lower=1 * MbPS)
    ).web_server(sim, num_bytes(expo(2 * KB), header=256 * B))

for domain in ["youtube.com", "netflix.com", "spotify.com"]:
    internet.host(
        domain,
        latency=normal(10 * MS, 20 * MS),
        bandwidth=bounded(expo(10 * MbPS), lower=1 * MbPS)
    ).web_server(
        sim,
        num_bytes(expo(2 * KB), header=256 * B),
        protocol=Protocol.SSL,
        frequency=4
    ).web_streaming(
        sim,
        bandwidth_usage=linear(expo(1 * MbPS), 1.0, 1 * MbPS),
        duration=expo(5 * MIN),
        frequency=1
    )

for domain in ["google.com", "facebook.com"]:
    internet.host(
        domain,
        latency=normal(10 * MS, 20 * MS),
        bandwidth=bounded(expo(10 * MbPS), lower=1 * MbPS)
    ).web_server(
        sim,
        num_bytes(expo(2 * KB), header=256 * B),
        protocol=Protocol.SSL
    ).websocket(
        # The response to a request on a HTTP[S] port by the host will contain suggestive information for running the
        # client part of the websocket exchange, as part of the payload dictionary.
        sim,
        duration=expo(5.0 * MIN),
        request_interval=expo(40.0 * S),
        update_interval=expo(10.0 * S),
        len_beacon=num_bytes(expo(1 * KB), header=256 * B)
    )

for domain in ["amazonaws.com", "digitalocean.com"]:
    internet.host(
        domain,
        latency=normal(10 * MS, 20 * MS),
        bandwidth=bounded(expo(10 * MbPS), lower=1 * MbPS)
    ).web_server(
        sim,
        num_bytes(expo(2 * KB), header=256 * B),
        protocol=Protocol.SSL,
        frequency=1
    ).shell_server(
        # The response to the first request on the SSH port by the host will contain suggestive information for running
        # the client part of the shell session, as part of the payload dictionary.
        sim,
        duration=expo(10.0 * MIN),
        interval=expo(5.0 * S),
        request=num_bytes(expo(200 * B), header=128 * B),
        response=num_bytes(expo(200 * B), header=128 * B)
    )


decision_exploit = uniform(0, 1)
len_response = num_bytes(expo(1 * KB), header=128 * B)


for hostname in ["mother.ru", "77.88.55.66"]:
    cnc_host = internet.host(
        hostname,
        latency=normal(100 * MS, 20 * MS),
        bandwidth=bounded(expo(100 * MbPS), lower=1 * MbPS)
    )

    @cnc_host.daemon(Protocol.TCP, 80, 433)
    def command_and_control(peer: Location, socket: Socket) -> None:
        socket.recv()
        socket.send(
            peer,
            next(len_response),
            Payload({PayloadDictionaryType.CONTENT: ("exploit" if next(decision_exploit) < 0.05 else "pong")})
        )


c2_host = internet.host("baidu-search.com", normal(200 * MS, 40 * MS), bounded(expo(1 * MbPS), lower=4 * KbPS))


@c2_host.daemon(Protocol.UDP, 80)
class C2(Daemon):

    def __init__(self) -> None:
        self._num_beacons: MutableMapping[str, int] = {}
        self._len_response = num_bytes(expo(2 * KB), header=128 * B)

    def handle_tcp_connection(self, peer: Location, socket: Socket):
        _, client_uuid = socket.recv()
        self._num_beacons.setdefault(client_uuid, 0)
        self._num_beacons[client_uuid] += 1
        if self._num_beacons[client_uuid] == 10:
            socket.send(peer, next(self._len_response) + 1 * KB, Payload({PayloadDictionaryType.CONTENT: "exploit"}))
        else:
            socket.send(peer, next(self._len_response), Payload({PayloadDictionaryType.CONTENT: "pong"}))

    def trigger(self, *args, **kwargs) -> None:
        self.handle_tcp_connection(*args, **kwargs)
