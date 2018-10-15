sim = Simulator()

internet = Internet(sim)

PORTS_DNS = [53]
PORTS_WWW = [80,443]
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
        port_forwarding((PORTS_WWW, ADDRESS_LOAD_BALANCER, PORTS_WWW))
    ),
    farm.connected_as(1).setup(  # On the FARM link, router will have address 10.1.128.1
        DHCP(),
        firewall(
            inbound=[
                allow(internet.cidr, TCP, PORTS_WWW),
                allow(internet.cidr, BOTH, PORTS_DNS),
                allow(CORP, TCP, PORTS_IT)
            ],
            outbound=[
                allow(internet.cidr, TCP, PORTS_WWW),
                allow(internet.cidr, BOTH, PORTS_DNS),
                DENY_ALL
            ]
        )
    ),
    corp.connected_as(1).setup(DHCP(), firewall()),  # On the CORP link, 10.1.64.1
    dc.connected_as(1).setup(  # On the DC link, 10.1.192.1
        DHCP(),
        firewall(
            inbound=[
                allow(internet.cidr, BOTH, PORTS_DNS),
                allow(CORP, TCP, PORTS_IT)
            ],
            outbound=[DENY_ALL]
        )
    )
)

assert set([farm, corp, dc]) == set(router.iter_lans())

NUM_ENDPOINTS_PER_NETWORK = 30
endpoints = [Endpoint(sim).connected_to(net) for _ in range(NUM_ENDPOINTS_PER_NETWORK) for net in [farm, corp, dc]]
assert all(ept.address_default == ad_address(0) for ept in endpoints)

sim.run()

all_addresses = set([as_address(net.cidr.network_address + 1) for net in [farm, corp, dc]]) | \
    set([ept.address_default for ept in endpoints])
for net in [farm, corp, dc]:
    assert len([addr for addr in all_addresses if addr in net]) == NUM_ENDPOINTS_PER_NETWORK + 1
