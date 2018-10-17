from inspect import isgenerator
from ipaddress import ip_network

from greensim.random import normal, constant
from itsim.link import Internet, Link
from itsim.node.endpoint import Endpoint
from itsim.node.router import Router
from itsim.simulator import Simulator
from itsim.types import as_address
from itsim.units import MS, GbPS
from itsim.network.services import DHCP, NAT
from itsim.network.services.firewall import Firewall, Allow, Deny, Protocol


sim = Simulator()

internet = Internet(sim)

PORTS_DNS = [53]
PORTS_WWW = [80, 443]

# A network link is a thing against which nodes connect, so as to communicate across an identified IP network.
net = Link("192.168.1.0/24", latency=normal(5 * MS, 1.5 * MS), bandwidth=constant(100 * GbPS))

assert net.cidr == ip_network("192.168.1.0/24")
for aname in ["latency", "bandwidth"]:
    assert hasattr(net, aname) and isgenerator(getattr(net, aname))


# A router is a node with interfaces connectable to multiple links, whose job is to forward packets between interfaces,
# as well as provide other ad hoc services. Its first parameter must be a connection to its WAN interface (which can be
# None if it does not forward outside of its local networks). Its other parameters are link connections to the LANs it
# forwards between. In this case, there is a single local network, so all forwarding is towards the WAN.
#
router = Router(
    internet.connected_as("24.192.132.23").setup(NAT()),  # WAN
    net.connected_as(1).setup(  # LAN -- As net is 192.168.1/24, machine 1 on it becomes 192.168.1.1.
        # Parameters to setup() are services we expect the router to run for this network.
        DHCP(),
        Firewall(
            inbound=[Allow(internet.cidr, Protocol.UDP, PORTS_DNS)],  # Allow DNS responses
            outbound=[                                  # Allow only website traffic
                Allow(internet.cidr, Protocol.TCP, PORTS_WWW),
                Allow(internet.cidr, Protocol.BOTH, PORTS_DNS),
                Deny.all()
            ]
        )
    )
)

nodes = set(net.iter_nodes())
assert len(nodes) == 1
assert router in nodes


# TODO -- Figure out how to list the services run by a node.
# TODO -- Have some nodes do something that the router's firewall would block, and capture this result.


# Instantiate nodes against the link.
# TODO -- Complete proper endpoint instantiation and load up some software.
# TODO -- Get endpoints to do some stuff against the Internet, and ensure it worked.
# TODO -- Facilitate adding multiple endpoints to a link in one call?
endpoints = [Endpoint(sim).connected_to(net) for _ in range(50)]

assert all(ept.address_default == as_address(0) for ept in endpoints)

nodes = set(net.iter_nodes())
assert len(nodes) == 1 + len(endpoints)
for ept in endpoints:
    assert ept in nodes

# Run the simulation.
sim.run()

all_addresses = set([as_address("192.168.1.1")])  # The router...
for ept in endpoints:
    assert ept.address_default in net.cidr
    all_addresses.add(ept.address_default)

# Make sure the nodes each have distinct addresses.
assert len(all_addresses) == 1 + len(endpoints)
