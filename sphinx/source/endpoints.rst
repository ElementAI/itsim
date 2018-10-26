============================
Adding endpoints to networks
============================

`Networks <networks>` in an IT infrastructure do nothing interesting without
workstations and servers communicating within them. Adding simple endpoints
within infrastructures is as simple as instantiating the
:py:class:`~itsim.node.endpoint.Endpoint` class and associating such instances
to outstanding links. Assuming a network has been already set up with a
:py:class:`itsim.network.link.Link` instance bound to variable ``local``, the
following sets up 50 endpoints onto this network::

    from itsim.node.endpoint import Endpoint
    for _ in range(50):
        Endpoint().connected_to(local)

These endpoints do not have any address set up to network with this ``local``
link they are connected to: their address is 0 (fully qualified 0.0.0.0). They
can rely on running a DHCP client **TBD** to get an address from the DHCP
server already running on the link, or they can set themselves up with a
static address. The following example shows this alternative::

    for n in range(50):
        Endpoint().connected_to(local, address=100 + n)

The ``address`` parameter to the :py:meth:`itsim.node.Node.connected_to`
method works like :ref:`that <address_fullyqual_machinenum>` of the
:py:meth:`itsim.network.link.Link.connected_as`
method. One can either specify a fully-qualified IP address as a string, or a
machine number, which is combined by bitwise OR to the link's own network
address.

**TBD: adding software and users**
