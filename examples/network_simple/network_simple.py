from greensim import Simulator

from itsim import MS, S, MIN, H, B, MB, GBPS, Location
from itsim.network import Network, Internet
from itsim.node import Router, Endpoint, CONNECTION_CLOSED
from itsim.software import random_network_activity


def agent_monitoring(node):
    node.on_connection_closed(report_connection)


def report_connection(node, connection):
    print("Connection!")


if __name__ == '__main__':
    with Simulator() as sim:
        internet = Internet(sim)

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
                random_network_activity(net_local, expo()),
                random_network_activity,
                agent_monitoring
            )
            for n in range(50)
        ]

        sim.run(72 * H)
