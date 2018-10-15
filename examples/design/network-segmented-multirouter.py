from itsim.link import Link, Internet
from itsim.node.endpoint import Endpoint
from itsim.node.router import Router
from itsim.random import normal, constant
from itsim.simulator import Simulator
from itsim.types import as_address
from itsim.units import MS, GbPS
from itsim.network.services import DHCP, NAT, PortForwarding
from itsim.network.services.firewall import Firewall, Allow, Deny, Protocol


sim = Simulator()

internet = Internet(sim)

PORTS_DNS = [53]
PORTS_WWW = [80,443]
PORTS_IT = [22] + list(range(135, 140)) + [445]

FARM = "10.1.128.0/18"
CORP = "10.1.64.0/18"
DC = "10.1.192.0/18"
LOBBY = "10.1.0.0/18"

ADDRESS_LOAD_BALANCER = "10.1.128.10"

lobby = Link(LOBBY, normal(5.0 * MS, 1.5 * MS), constant(1 * GbPS))
router_main = Router(
    internet.connected_as("24.192.132.23").setup(
        NAT(),  # Router will operate network address translation when forwarding on WAN.
        PortForwarding({port: (ADDRESS_LOAD_BALANCER, port) for port in PORTS_WWW})
    ),
    lobby.connected_as(1).setup(
        Firewall(
            inbound=[
                Allow(internet.cidr, Protocol.TCP, PORTS_WWW),
                Allow(internet.cidr, Protocol.BOTH, PORTS_DNS)
            ]
            # Default outbound rules: let everything through.
        )
    )
)

farm = Link(FARM, normal(5.0 * MS, 1.5 * MS), constant(1 * GbPS))
router_farm = Router(
    lobby.connected_as(2).setup(),
    farm.connected_as(1).setup(
        DHCP(),
        Firewall(
            inbound=[
                Allow(internet.cidr, Protocol.TCP, PORTS_WWW),
                Allow(internet.cidr, Protocol.BOTH, PORTS_DNS),
                Allow(CORP, Protocol.TCP, PORTS_IT)
            ],
            outbound=[
                Allow(internet.cidr, Protocol.TCP, PORTS_WWW),
                Allow(internet.cidr, Protocol.BOTH, PORTS_DNS),
                Deny.ALL
            ]
        )
    )
)

corp = Link(CORP, normal(5.0 * MS, 1.5 * MS), constant(1 * GbPS))
router_corp = Router(
    lobby.connected_as(3).setup(),
    corp.connected_as(1).setup(DHCP(), Firewall())
)

dc = Link(DC, normal(5.0 * MS, 1.5 * MS), constant(1 * GbPS))
router_dc = Router(
    lobby.connected_as(4).setup(),
    dc.connected_as(1).setup(
        DHCP(),
        Firewall(
            inbound=[
                Allow(internet.cidr, Protocol.BOTH, PORTS_DNS),
                Allow(CORP, Protocol.TCP, PORTS_IT)
            ],
            outbound=[Deny.ALL]
        )
    )
)

assert {router_main, router_farm, router_corp, router_dc} == set(lobby.iter_nodes())

NUM_ENDPOINTS_PER_SUBNET = 30
endpoints = [Endpoint(sim).link_to(net) for _ in range(NUM_ENDPOINTS_PER_SUBNET) for net in [farm, corp, dc]]
assert all(ept.address_default == ad_address(0) for ept in endpoints)

sim.run()

NUM_ADDRESSES_INTERNET = 1
NUM_ADDRESSES_LOBBY = 4
all_addresses = set()
for net in [lobby, farm, corp, dc]:
    for node in net.iter_nodes():
        for addr in node.iter_addresses():
            all_addresses.add(addr)
assert len(all_addresses) == NUM_ADDRESSES_INTERNET + NUM_ADDRESSES_LOBBY + 3 * NUM_ENDPOINTS_PER_SUBNET
