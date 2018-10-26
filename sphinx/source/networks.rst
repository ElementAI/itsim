===================
Setting up networks
===================

In ITsim, a *network* is the composition of two discrete components: a set of
:py:class:`~itsim.network.link.Link` instances, which represent a logical
medium binding together a set of nodes, so that they may communicate over an
intended IP network; and a :py:class:`~itsim.node.router.Router` instance, a
node that articulates packet forwarding between connected routers, as well as
other modern networking services. The following sections illustrate how to set
up increasingly complex networks, given that such network constructions can in
turn be themselves thus composed.


Prelude: the Internet
=====================

While it is possible to simulate a local network outside of a global
communications environment, typical IT infrastructures do connect to such an
environment. It is here represented as an instance of the
:py:class:`~itsim.network.internet.Internet` class, which is deployed as a
special kind of *link*. We will :doc:`return <internet>` to setting up a
realistic Internet environment against certain needs. For the time being, the
following examples all assume that an Internet has been instantiated::

    from itsim.network.internet import Internet
    internet = Internet()


.. _flat:

The simplest network, with a flat architecture
==============================================

As mentioned above, a network is composed of links and routers. A flat network
would connect all nodes together, without any segmentation. This network would
be bound to the internet through a single router, which would perform network
address translation against the Internet, and provide firewall and DHCP
service to the network. This is a common home network configuration.

Given all nodes on this network are connected, a single
:py:class:`~itsim.network.link.Link` instance suffices. It is configured with
the intended *network address* (expressed in CIDR form). We must also specify
*probability models* for its latency and bandwidth. These are pseudo-random
generators that express the variability of these properties for the network.
These generators are both sampled from for every packet that must be
transmitted over the link. Note that neither quantity can be expressed with a
negative number: thus, the probability models provided when instantiating the
link are *clipped* when sampled -- any negative value sampled from these
generators are replaced with 0. ::

    from greensim.random import normal, constant
    from itsim.network import Link
    from itsim.units import MS, MbPS

    local = Link(
        "192.168.1.0/24",
        latency=normal(0.1 * MS, 0.01 * MS),
        bandwidth=constant(100 * MbPS)
    )

Remark that the ``latency`` and ``bandwidth`` parameter need not be named;
they were named here for documentation's sake.

This budding network now needs a router. Let's instantiate it and then explain
what is going on with it. ::

    from itsim.network.router import Router
    from itsim.network.services import NAT, DHCP
    from itsim.network.services.firewall import Firewall

    router = Router(
        internet.connected_as("24.192.132.23").setup(NAT()),
        local.connected_as(1).setup(DHCP(), Firewall())
    )

A lot of things are going on here, so let us break it down. The
:py:class:`~itsim.node.router.Router` instantiation bears two parameters: the
result of :py:meth:`~itsim.network.link.Connection.setup` applied to the
result of :py:meth:`~itsim.network.link.Link.connected_as`.
These two parameters correspond, respectively, to the configuration of the WAN
and LAN interface. As we will see :ref:`later <segmented-1router>`, the router
has a single WAN interface, but may bind together any number of LANs.

.. _address_fullyqual_machinenum:

The :py:meth:`~itsim.network.link.Link.connected_as` method indicates how
the router is meant to be connected to each of the ``internet`` and ``local``
links. The parameter is the IP address meant for the router on these links,
either fully qualified (as ``"24.192.132.23"``), or expressed as a machine
number to bitwise-OR to the link's network number (as ``1``, which
bitwise-ORed to 192.168.1.0/24 is expressed as 192.168.1.1 in fully qualified
form).

The result of the :py:meth:`~itsim.network.link.Link.connected_as` method is
an :py:class:`~itsim.network.link.Connection` object for which a
:py:meth:`~itsim.network.link.Connection.setup` method can be called in turn,
which indicates the services the router should enact against this link. In the
case of the Internet link, the router must implement NATting (hence the
:py:class:`~itsim.network.service.NAT` service instantiation); in that of the
local network, it must implement :py:class:`~itsim.network.service.DHCP`
address distribution and a
:py:class:`~itsim.network.service.firewall.Firewall`). The latter has the
default configuration of allowing all packets outbound, but none inbound.

This interface is rather complicating for setting up a simple network, but it
enables the flexibility required for more complicated architectures.

.. _segmented-1router:

Segmented network with a single router
======================================

So, the job of a router is not merely to forward between a LAN and a WAN -- it
will also readily forward between multiple LANs. This is how we can leverage a
single router to implement a segmented network, with each segment hosted on
its own :py:class:`~itsim.network.link.Link`. In this example, consider an
organization splitting the class-B address space 10.1.0.0/16. We will consider
three segments, each with its own needs in terms of communications:

#. The server farm, subnet 10.1.128.0/18 is where the organization's web
   servers are made to live.  HTTP and HTTPS requests (ports 80 and 443,
   respectively) from the Internet are fielded by nodes on this subnet. Nodes
   on this segment, to facilitate deployment, are also enabled to resolve
   domain names and to conduct Internet requests of their own. In particular,
   the farm hosts a load balancer for HTTP requests at 10.1.128.10.
#. The corporate network, subnet 10.1.64.0/18, hosts the workstations of the
   employees of the organization. This follows the usual firewall rules: allow
   nothing inbound, allow everything outbound.
#. The data center, subnet 10.1.192.0/18, must be protected, as it hosts the
   organization's confidential digital assets. This subnet allows Windows
   sharing and SSH connections from the corporate subnet only, and denies
   all outbound communications from its nodes.

The code to implement this network::

    from greensim.random import normal, constant
    from itsim.network import Link
    from itsim.network.router import Router
    from itsim.network.services import NAT, DHCP, PortForwarding
    from itsim.network.services.firewall import Firewall, Allow, Deny
    from itsim.types import Protocol
    from itsim.units import MS, MbPS

    PORTS_DNS = [53]
    PORTS_WWW = [80, 443]
    PORTS_IT = [22, 445] + list(range(135, 140))

    farm = Link("10.1.128.0/18", normal(0.1 * MS, 0.01 * MS), constant(100 * MbPS))
    corp = Link("10.1.64.0/18", normal(0.1 * MS, 0.01 * MS), constant(100 * MbPS))
    dc = Link("10.1.192.0/18", normal(0.1 * MS, 0.01 * MS), constant(100 * MbPS))

    router = Router(
        internet.connected_as("24.192.132.23").setup(
            NAT(),
            PortForwarding({port: (ADDRESS_LOAD_BALANCER, port) for port in PORTS_WWW})
        ),
        farm.connected_as(1).setup(
            DHCP(),
            Firewall(
                inbound=[
                    Allow(internet.cidr, Protocol.TCP, PORTS_WWW),
                    Allow(internet.cidr, Protocol.BOTH, PORTS_DNS),
                    Allow("10.1.64.0/18", Protocol.TCP, PORTS_IT)
                ],
                outbound=[
                    Allow(internet.cidr, Protocol.TCP, PORTS_WWW),
                    Allow(internet.cidr, Protocol.BOTH, PORTS_DNS),
                    Deny.all()
                ]
            )
        ),
        corp.connected_as(1).setup(DHCP(), Firewall()),
        dc.connected_as(1).setup(
            DHCP(),
            Firewall(
                inbound=[
                    Allow(internet.cidr, Protocol.BOTH, PORTS_DNS),
                    Allow("10.1.64.0/18", Protocol.TCP, PORTS_IT)
                ],
                outbound=[Deny.all()]
            )
        )
    )

Beyond the generalization of the :ref:`flat network <flat>` to connecting
multiple LAN links to the router, two new details have emerged. The first is
the configuration of a port forwarding service on the WAN interface
(:py:class:`~itsim.network.service.PortForwarding`), which is set up to carry
certain inbound ports to a specific node on the local network.

The second detail is the configuration of the LAN firewalls with ``inbound``
and ``outbound`` rules. Such rules are applied in sequence, and prepended to
the default firewall rules (deny all inbound, allow all outbound). The first
applicable rule determines what to do with an inbound or outbound packet. All
subnets allow full DNS traffic. Things get more complicated Thus, we see the
farm firewall allows in HTTP(S) traffic and corporate traffic (Windows sharing
and SSH), and only HTTP(S) traffic out; the corporate network has no special
rule; the data center network allows in only corporate traffic, and blocks
everything outbound.


.. _segmented-multirouter:

Multi-router segmented network
==============================

We may imagine that the previous network may be alternatively set up with
multiple simpler networks, all bound to their respective router. These routers
would meet over an ad hoc subnet, the *lobby* (subnet 10.1.0.0/18), which
would be connected to the Internet by yet another router. Here is how this can
be encoded::

    from greensim.random import normal, constant
    from itsim.network import Link
    from itsim.network.router import Router
    from itsim.network.services import NAT, DHCP, PortForwarding
    from itsim.network.services.firewall import Firewall, Allow, Deny
    from itsim.types import Protocol
    from itsim.units import MS, MbPS

    PORTS_DNS = [53]
    PORTS_WWW = [80, 443]
    PORTS_IT = [22, 445] + list(range(135, 140))

    lobby = Link("10.1.0.0/18", normal(0.1 * MS, 0.01 * MS), constant(100 * MbPS))
    gateway = Router(
        internet.connected_as("24.192.132.23").setup(
            NAT(),
            PortForwarding({port: (ADDRESS_LOAD_BALANCER, port) for port in PORTS_WWW})
        ),
        lobby.connected_as(1).setup(
            Firewall(
                inbound=[
                    Allow(internet.cidr, Protocol.TCP, PORTS_WWW),
                    Allow(internet.cidr, Protocol.BOTH, PORTS_DNS)
                ]
            )
        )
    )

    farm = Link("10.1.128.0/18", normal(0.1 * MS, 0.01 * MS), constant(100 * MbPS))
    router_farm = Router(
        lobby.connected_as(2).setup(),
        farm.connected_as(1).setup(
            DHCP(),
            Firewall(
                inbound=[
                    Allow(internet.cidr, Protocol.TCP, PORTS_WWW),
                    Allow(internet.cidr, Protocol.BOTH, PORTS_DNS),
                    Allow("10.1.64.0/18", Protocol.TCP, PORTS_IT)
                ],
                outbound=[
                    Allow(internet.cidr, Protocol.TCP, PORTS_WWW),
                    Allow(internet.cidr, Protocol.BOTH, PORTS_DNS),
                    Deny.all()
                ]
            )
        )
    )

    corp = Link("10.1.64.0/18", normal(0.1 * MS, 0.01 * MS), constant(100 * MbPS))
    router_corp = Router(
        lobby.connected_as(3).setup(),
        corp.connected_as(1).setup(DHCP(), Firewall())
    )

    dc = Link("10.1.192.0/18", normal(0.1 * MS, 0.01 * MS), constant(100 * MbPS))
    router_dc = Router(
        lobby.connected_as(4).setup(),
        dc.connected_as(1).setup(
            DHCP(),
            Firewall(
                inbound=[
                    Allow(internet.cidr, Protocol.BOTH, PORTS_DNS),
                    Allow("10.1.64.0/18", Protocol.TCP, PORTS_IT)
                ],
                outbound=[Deny.all()]
            )
        )
    )

The difference is that for the farm, corporate and data center subnets, the
WAN interface has connected to the lobby link. The gateway does not perform
DHCP service, so each router on the lobby assigns itself a static address.
Under the hood, the various routers on a given network exchange forwarding
information so that they each know how to properly forward packets between
subnets.
