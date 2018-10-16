from typing import Optional, MutableMapping

from greensim.random import expo, normal, bounded, linear

from itsim.it_objects import Socket
from itsim.link import Internet, Daemon
from itsim.random import num_bytes
from itsim.simulator import Simulator
from itsim.units import KB, MbPS, MIN, S


sim = Simulator()
internet = Internet()


for address in ["8.8.8.8", "8.8.4.4"]:
    internet.host(address, latency=normal(10 * MS, 5 * MS), bandwidth=bounded(10 * MbPS, lower=1 * MbPS))
        .dns(sim)

for domain in ["newyorker.com", "amazon.com"]:
    internet.host(domain, latency=normal(10 * MS, 20 * MS), bandwidth=bounded(10 * MbPS, lower=1 * MbPS))
        .web_server(sim, num_bytes(expo(2 * KB), header=256 * B))

for domain in ["youtube.com", "netflix.com", "spotify.com"]:
    internet.host(domain, latency=normal(10 * MS, 20 * MS), bandwidth=bounded(10 * MbPS, lower=1 * MbPS))
        .web_server(sim, num_bytes(expo(2 * kB), header=256 * B), ports=443, frequency=4)
        .web_streaming(
            sim,
            bandwidth_usage=linear(expo(1 * MbPS), 1.0, 1 * MbPS),
            duration=expo(5 * MIN), frequency=1
        )

for domain in ["google.com", "facebook.com"]:
    # The response to a request on a HTTP[S] port by the host will contain suggestive information for running the client
    # part of the websocket exchange, as part of the payload dictionary.
    internet.host(domain, latency=normal(10 * MS, 20 * MS, bandwidth=bounded(10 * MbPS, lower=1 * MbPS))
        .web_server(sim, num_bytes(expo(2 * KB), header=256 * B))
        .websocket(
            duration=expo(5.0 * MIN),
            request_interval=expo(40.0 * S),
            update_interval=expo(10.0 * S),
            len_beacon=num_bytes(expo(1 * KB), header=256 * B)
        )

for domain in ["amazonaws.com", "digitalocean.com"]:
    internet.host(domain, latency=normal(10 * MS, 20 * MS), bandwidth=bounded(10 * MbPS, lower=1 * MbPS))
        .web_server(num_bytes(expo(2 * KB), header=256 * B), ports=443, frequency=1)
        # The response to the first request on the SSH port by the host will contain suggestive information for running
        # the client part of the shell session, as part of the payload dictionary.
        .secure_shell(
            duration=expo(10.0 * MIN),
            interval=expo(5.0 * S),
            request=num_bytes(expo(200 * B), header=128 * B),
            response=num_bytes(expo(200 * B), header=128 * B),
            ports=22
        )


decision_exploit = uniform(0, 1)
len_response = num_bytes(expo(1 * KB), header=128 * B)

@internet.host(("mother.ru", "77.88.55.66")).custom(sim, tcp=[80, 443])
def command_and_control(socket: Socket):
    socket.recv()
    lr = next(len_response)
    socket.send(next(len_response), "exploit" if next(decision_exploit) < 0.05 else "pong")


@internet.host("baidu-search.com").custom(sim, udp=80)
class C2(Daemon):

    def __init__(self, sim: Simulator, tcp: Optional[PortsRepr] = None, udp: Optional[PortsRepr] = None):
        super().__init__(sim, tcp, udp)
        self._num_beacons: MutableMapping[str, int] = {}
        self._len_response = num_bytes(expo(2 * KB), header=128 * B)

    def handle_tcp_connection(self, socket):
        _, client_uuid = socket.recv()
        self._num_beacons.setdefault(client_uuid, 0)
        self._num_beacons[client_uuid] += 1
        if self._num_beacons[client_uuid] == 10:
            socket.send(next(self._len_response) + 1 * KB, "exploit")
        else:
            socket.send(next(self._len_response), "pong")
