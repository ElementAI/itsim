=========================
Setting up Internet hosts
=========================

Local networking is fun, but the good stuff is all on the Internet. To
simulate users communicating with various services on the Internet, special
nodes implicitly connected to the Internet as a ``Link`` instance can be set
up. We call these *Internet hosts*.


Instantiation
=============

From an `itsim.network.internet.Internet` instance, we can instantiate and
build Internet hosts by invoking the `host()` method. Like instantiating local
links, we must specify probability models for the communication properties of
the implicit link between the local network and this node::

    from greensim.random import normal, expo
    from itsim.network.internet import Internet
    from itsim.units import MS, MbPS

    internet = Internet()
    internet.host(
        "24.56.89.12",
        latency=normal(10 * MS, 5 * MS),
        bandwidth=expo(10 * MbPS)
    )

The host above does nothing, so the following shows how to add connectivity to
various common services. Note that the address may also be a domain name: the
Internet link will, will take DNS resolution into account when simulating the
timing of packet delivery.


Domain name service (DNS)
=========================

Add DNS service over both UDP and TCP, on port 53::

    from itsim.simulator import Simulator

    sim = Simulator()
    internet.host("8.8.8.8", normal(10 * MS, 5 * MS), expo(20 * MbPS)).dns(sim)

Simple! Notice how each service, as an agent for resolving an intent within
the simulated world, must be set up with a ``Simulator`` instance.


Web servers (HTTP and HTTPS)
============================

The ``web_server()`` method of the ``itsim.node.Node`` instance returned by
``Internet.host()`` sets up a web server over a common port. The communication
paradigm involves the host sending one request, then getting one response,
after which the TCP connection is closed. Whatever the length of the request
issued, the length of the response is sampled from a probability model
provided at setup. Example::

    from itsim.random import num_bytes
    from itsim.types import Protocol
    from itsim.units import B, KB

    internet.host("nytimes.com", normal(10 * MS, 10 * MS), expo(10 * MbPS)).web_server(
        sim,
        len_response=num_bytes(expo(2 * KB), header=256 * B),
        protocol=Protocol.ANY
    )

The ``num_bytes()`` probability model wraps around a continuous model,
projecting its samples to the nearest int, and adding a systematic fixed
number of bytes acting as header to the packet or buffer. The ``protocol``
parameter specifies here that service should be provided on both cleartext
or crypted protocols, hence both HTTP and HTTPS; clients will thus be able to
connect to both ports 80 and 443. The alternatives are ``Protocol.CLEAR`` and
``Protocol.SSL`` to limit the connectivity possibilities.


Streaming service over HTTP(S)
==============================

When hosts implement regular HTTP(S) service, they may allow a certain number
of requests to the host to yield a *streamed response*. This allows modeling
audio/video streaming services, such as youtube.com. The stream server is set
up so that the duration of the response to a request is sampled from a
probability model; the bandwidth used during the response streaming is also
sampled from a distinct model. During this time, a sequence of packet will be
sent to the request sender so that the a sampled bandwidth is filled. Given
that stream servers are also used as normal request-reply web servers, the
relative frequency of normal and streaming requests must be set. Example::

    from greensim.random import linear
    from itsim.units import MIN, S

    internet.host("youtube.com", normal(10 * MS, 5 * MS), expo(20 * MbPS)).web_server(
        sim,
        num_bytes(expo(4 * KB), header=256 * B),
        Protocol.SSL,
        frequency=4
    ).web_streaming(
        sim,
        bandwidth_usage=linear(expo(1 * MbPS), 1.0, 1 * MbPS),
        duration=expo(5 * MIN),
        protocol=Protocol.SSL,
        frequency=1
    )

Notice the build pattern: each of the service returns the host instance, so
multiple services can be thus chained. Also, the previous example suggested
that normal request-reply communication happens 4 times as often as streaming
communication. The type of communication enacted following a request will be
determined at random by the host instance in accordance with these relative
frequencies.


Websocket communications
========================

Many web servers, once they have sent the initial reply to a request, will
maintain the connection open, so as to provide further services over *web
sockets*. In this paradigm, the web page rendered by a browser on a client
node will run Javascript automation that performs yet more requests over the
connection, each getting a single reply. In addition, the server can push
unsollicited updates. The whole session lasts until some event forcibly
terminates the connection, such as the page being closed by the browser, or
the node is cut off from the network. To set up a domain running a web sockets
session::

    internet.host("google.com", normal(10 * MS, 10 * MS), expo(10 * MbPS)).web_server(
        sim,
        num_bytes(expo(4 * KB), header=256 * B),
        protocol=Protocol.SSL
    ).websocket(
        sim,
        duration=expo(5.0 * MIN),
        request_interval=expo(40.0 * S),
        update_interval=expo(10.0 * S),
        len_beacon=num_bytes(expo(1 * KB), header=256 * B)
    )

Multiple probability models are put in play here. In order:

#. The duration of the session
#. The time interval between requests (suggested to the client browser)
#. The time interval between updates (forced from the server)
#. The length of beacons sent by the server (whether from a request or as an
   update).


Shell service (SSH)
===================

Some hosts allow clients to connect to a an interactive shell session: over
the course of a TCP connection, they are made to exchange repeated requests
and responses, with a certain time interval separating these request-response
pairs. Example::

    internet.host("amazonaws.com", normal(10 * MS, 20 * MS), expo(5 * MbPS)).shell_server(
        sim,
        duration=expo(10.0 * MIN),
        interval=expo(5.0 * S),
        request=num_bytes(expo(200 * B), header=60 * B),
        response=num_bytes(expo(200 * B), header=60 * B)
    )

Much of the process is driven by the client, whom gets suggested the various
models for the duration of the connection, the interval between requests and
the size of request packets.


Custom daemon
=============

Should a service to model not be implemented, one can always implement their
own, by using the ``Internet.daemon`` decorator method. To implement a
stateless service, one can thus decorate a function articulating the
server-side logic::

    from itsim.network.location import Location
    from itsim.node.socket import Socket

    h = internet.host("mydomain.com", normal(10 * MS, 4 * MS), expo(1 * MbPS))

    @h.daemon(sim, udp=[67,68])
    def my_own_dhcp_server(peer: Location, socket: Socket) -> None:
        # Code for running the connection goes here.

Alternatively, one may implement a stateful connection through similarly
decorating a class. The class is instantiated by the ``daemon()`` decorator
method and is used to manage all packets delivered to the locations indicated
by the ``tcp`` and ``udp`` parameters to the decorator. The decorated class
must subclass ``itsim.network.internet.Daemon``, as as such may override any
of its inner workings. **TBD: enhance this example.** ::

    from itsim.network.internet import Daemon

    @h.daemon(sim, tcp=[9887,49887], udp=[39887]):
    class Malware(Daemon):
        # Override methods here.
