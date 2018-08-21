from greensim import Simulator, happens
from greensim.random import constant, expo, normal, distribution

from itsim import MS, S, MIN, H, B, MB, Location
from itsim.network import Network, Internet
from itsim.node import Router, Endpoint
from itsim.random import num_bytes
from itsim.software import RandomNetworkActivity


LOCATION_C2 = [
    Location(host, port) for host, port in
    [
        ("2.7.45.67", 80),
        ("rom.com", 8080),
        ("8.45.90.222", 80),
        ("intelligent.design", 8081)
    ]
]
location_c2 = distribution(LOCATION_C2)
len_beacon = num_bytes(expo(1024 * B), header=128 * B, max=20 * MB)
len_response = num_bytes(expo(384 * B), header=128 * B, max=1.5 * MB)


def agent_monitoring(node):
    node.hook("connection_closed", report_connection)


def report_connection(node, connection):
    print("Connection!")


@happens(uniform(2.1 * H, 4.9 * H), "malware")
def malware(node):
    with node.tcp_connect(next(location_c2)) as connection:
        connection.send(next(len_beacon))
        connection.recv()


def c2_server(connection):
    connection.recv()
    connection.send(next(len_response))


if __name__ == '__main__':
    sim = Simulator()

    internet = Internet(sim)
    for loc in LOCATION_C2:
        internet.add_receiver(loc, c2_server)

    net_local = Network(
        sim,
        cidr="192.168.4.0/24",
        bandwidth=constant(1 * GBPS),
        latency=normal(5 * MS, 1 * MS),
        num_skip_addresses=100
    )
    router = Router(net_local, internet)
    workstations = [
        Endpoint(f"Workstation-{n+1}", net_local).install(
            random_network_activity,  # INCOMPLETE
            random_network_activity,
            agent_monitoring
        )
        for n in range(50)
    ]
    workstations[23].install(malware)

    sim.run(72 * H)
