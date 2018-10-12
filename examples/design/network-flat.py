from inspect import isgenerator

sim = Simulator()


internet = Internet(sim)
INTERNET = internet.cidr

PORTS_DNS = [53]
PORTS_WWW = [80, 443]

# A network link is a thing against which nodes connect, so as to communicate across an identified IP network.
net = Link("192.168.1/24", latency=normal(5 * MS, 1.5 * MS), bandwidth=constant(100 * GbPS))

assert net.cidr == ip_network("192.168.1/24")
for aname in ["latency", "bandwidth"]:
    assert hasattr(net, aname) and isgenerator(getattr(net, aname))


# A router is a node with interfaces connectable to multiple links, whose job is to forward packets between interfaces,
# as well as provide other ad hoc services. Its first parameter must be a connection to its WAN interface (which can be
# None if it does not forward outside of its local networks). Its other parameters are link connections to the LANs it
# forwards between. In this case, there is a single local network, so all forwarding is towards the WAN.
#
router = Router(
    wan=internet.connected_as("24.192.132.23"),
    net.connected_as(1).setup(  # As net is 192.168.1/24, machine 1 on it becomes 192.168.1.1.
        # Parameters to setup() are services we expect the router to run for this network.
        DHCP(),
        firewall(
            inbound=[allow(INTERNET, UDP, PORTS_DNS)],  # Allow DNS responses
            outbound=[                                  # Allow only website traffic
                allow(INTERNET, TCP, PORTS_WWW),
                allow(INTERNET, BOTH, PORTS_DNS),
                deny_all()
            ]
        )
    )
)

nodes = set(net.iter_nodes())
assert len(nodes) == 1
assert router in nodes


# TODO -- Figure out how to list the services run by a node.
# TODO -- Assert that the router node is doing DHCP against


# Instantiate nodes against the link.
# TODO -- Complete proper endpoint instantiation and load up some software.
# TODO -- Get endpoints to do some stuff against the Internet, and ensure it worked.
endpoints = [Endpoint(sim).connected_to(net) for _ in range(50)]

assert all(ept.address_default == as_address(0) for ept in endpoints)

nodes = set(net.iter_nodes())
assert len(nodes) == 1 + len(endpoints)
for ept in endpoints:
    assert ept in nodes

# Run the simulation.
sim.run()

all_addresses = set(as_address("192.168.1.1"))  # The router...
for ept in endpoints:
    assert ept.address_default in net.cidr
    all_addresses.add(ept.address_default)

# Make sure the nodes each have distinct addresses.
assert len(all_addresses) == 1 + len(endpoints)
