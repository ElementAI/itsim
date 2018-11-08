from greensim.random import normal, constant

from itsim.network.link import Link
from itsim.network.internet import Internet
from itsim.network.service import DHCP, NAT, PortForwarding
from itsim.network.service.firewall import Firewall, Allow, Deny, Protocol
from itsim.machine.endpoint import Endpoint
from itsim.machine.router import Router
from itsim.simulator import Simulator
from itsim.types import as_address
from itsim.units import MS, GbPS


sim = Simulator()
internet = Internet()

PORTS_DNS = [53]
PORTS_WWW = [80, 443]
PORTS_IT = [22] + list(range(135, 140)) + [445]

FARM = "10.1.128.0/18"
CORP = "10.1.64.0/18"
DC = "10.1.192.0/18"

ADDRESS_LOAD_BALANCER = "10.1.128.10"

farm = Link(FARM, normal(5.0 * MS, 1.5 * MS), constant(1 * GbPS))
corp = Link(CORP, normal(5.0 * MS, 1.5 * MS), constant(1 * GbPS))
dc = Link(DC, normal(5.0 * MS, 1.5 * MS), constant(1 * GbPS))

router = Router(
    internet.connected_as("24.192.132.23").setup(
        NAT(),  # Router will operate network address translation when forwarding on WAN.
        PortForwarding({port: (ADDRESS_LOAD_BALANCER, port) for port in PORTS_WWW})
    ),
    farm.connected_as(1).setup(  # On the FARM link, router will have address 10.1.128.1
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
                Deny.all()
            ]
        )
    ),
    corp.connected_as(1).setup(DHCP(), Firewall()),  # On the CORP link, 10.1.64.1
    dc.connected_as(1).setup(  # On the DC link, 10.1.192.1
        DHCP(),
        Firewall(
            inbound=[
                Allow(internet.cidr, Protocol.BOTH, PORTS_DNS),
                Allow(CORP, Protocol.TCP, PORTS_IT)
            ],
            outbound=[Deny.all()]
        )
    )
)

assert set([farm, corp, dc]) == set(router.iter_lans())

NUM_ENDPOINTS_PER_NETWORK = 30
endpoints = [Endpoint().connected_to(net) for _ in range(NUM_ENDPOINTS_PER_NETWORK) for net in [farm, corp, dc]]
assert all(ept.address_default == as_address(0) for ept in endpoints)

sim.run()

all_addresses = set([as_address(net.cidr.network_address + 1) for net in [farm, corp, dc]]) | \
    set([ept.address_default for ept in endpoints])
for net in [farm, corp, dc]:
    assert len([addr for addr in all_addresses if addr in net.cidr]) == NUM_ENDPOINTS_PER_NETWORK + 1
