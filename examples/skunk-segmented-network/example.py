from itsim.network import network, INTERNET
from itsim.network.services import DHCP
from itsim.network.firewall import allow, deny, deny_all, BOTH, TCP, UDP, BOTH

LOBBY = "10.1.0.0/18"
FARM = "10.1.128.0/18"
CORP = "10.1.64.0/18"
DATA = "10.1.192.0/18"

ADDRESS_LOAD_BALANCER = "10.1.128.10"

PORTS_IT = [22] + list(range(135, 140)) + [445]
PORTS_WEB = [80, 443]
PORTS_DNS = [53]

link_performance = LinkPerformance(normal(5 * MS, 1.5 * MS), bandwidth=constant(1 * GbPS))

link = network(
    "24.192.132.23",
    LOBBY,
    gateway="10.1.0.1",
    link_performance=link_performance,
    subnets=[
        network(
            "10.1.0.2",
            FARM,
            gateway="10.1.128.1",   # Not mandatory -- sane default.
            link_performance=link_performance,
            inbound=[
                (INTERNET, TCP, PORTS_WWW, ALLOW),
                (INTERNET, BOTH, PORTS_DNS, ALLOW),
                (CORP, TCP, PORTS_IT, ALLOW)
            ],
            outbound=[
                (INTERNET, TCP, PORTS_WWW, ALLOW),
                (INTERNET, BOTH, PORTS_DNS, ALLOW),
                DENY_ALL
            ],
            services=[DHCP]
        ),
        network("10.1.0.3", CORP, link_performance, services=[DHCP]),
        network(
            "10.1.0.4",
            DATA,
            link_performance=link_performance,
            inbound=[
                (INTERNET, BOTH, PORTS_DNS, ALLOW),
                (CORP, TCP, PORTS_IT, ALLOW)
            ],
            outbound=[DENY_ALL],
            services=[DHCP]
        )
    ],
    nat=True,
    port_forwarding=[
        (PORTS_WWW, ADDRESS_LOAD_BALANCER, PORTS_WWW)
    ]
)

# The result is a map of network CIDR prefixes to link instances, which can then be used to tie workstations.
ws = Workstation().linked_to(link[CORP])


# Alternative:
internet = Internet()

lobby = network(
    { "24.192.132.23": internet },
    LOBBY,
    link_performance,
    router="10.1.0.1",  # Not necessary.
    nat=True,
    port_forwarding=[
        (PORTS_WWW, ADDRESS_LOAD_BALANCER, PORTS_WWW)
    ]
)

corp = network({ "10.1.0.3": lobby }, CORP, link_performance, services=[DHCP])

farm = network(
    { "10.1.0.2": lobby },
    FARM,
    link_performance,
    inbound=[
        allow(INTERNET, TCP, PORTS_WWW),
        allow(INTERNET, BOTH, PORTS_DNS, ALLOW),
        allow(corp, TCP, PORTS_IT, ALLOW)
    ],
    outbound=[
        allow(INTERNET, TCP, PORTS_WWW),
        allow(INTERNET, BOTH, PORTS_DNS),
        deny_all()
    ],
    services=[DHCP]
)

data = network(
    { "10.1.0.4": lobby },
    DATA,
    link_performance,
    inbound=[allow(corp, TCP, PORTS_IT)],
    outbound=[deny_all()],
    services=[DHCP]
)


