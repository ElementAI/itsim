from collections import OrderedDict
from itertools import cycle
from typing import Callable, MutableMapping, Optional, Set, Iterator, List, cast, Tuple, Union

from itsim.network.forwarding import Forwarding
from itsim.network.interface import Interface
from itsim.network.link import Link, Loopback
from itsim.network.location import Location
from itsim.network.packet import Packet
from itsim.network.service.dhcp import dhcp_client
from itsim.machine import _Node
from itsim.machine.file_system import File
from itsim.machine.process_management.daemon import Daemon
from itsim.machine.process_management.process import Process
from itsim.machine.process_management.thread import Thread
from itsim.machine.socket import Socket
from itsim.machine.user_management import UserAccount
from itsim.simulator import Simulator
from itsim.types import Address, AddressRepr, as_address, as_port, Cidr, Hostname, Port, PortRepr, Protocol, Payload

from itsim.schemas.itsim_items import create_json_item
from itsim.time import now_iso8601
from collections import defaultdict
from itsim import ITObject

PORT_NULL = 0
PORT_MAX = 2 ** 16 - 1
PORT_EPHEMERAL_MIN = 32768
PORT_EPHEMERAL_UPPER = 61000
NUM_PORTS_EPHEMERAL = PORT_EPHEMERAL_UPPER - PORT_EPHEMERAL_MIN


class NameNotFound(Exception):
    """
    Raised when a domain name cannot be resolved to an IP address.
    """

    def __init__(self, name: Hostname) -> None:
        super().__init__()
        self.name = name


class PortAlreadyInUse(Exception):
    """
    Raised when attempting to :py:meth:`Node.bind` a socket that is already bound and for which the :py:class:`Socket`
    has not yet been :py:meth:`Socket.close`'d.
    """

    def __init__(self, port: Port) -> None:
        super().__init__()
        self.port = port


class EphemeralPortsAllInUse(Exception):
    """
    Raised when trying to allocate an ephemeral port while all of them are in use on the endpoint.
    """
    pass


class NoRouteToHost(Exception):
    """
    Raised when attempting to send a packet to a destination address for which the node knows no route.
    """

    def __init__(self, address: Address) -> None:
        super().__init__()
        self.address = address



# ------------------------------------------------
#   Communication Agent (to be used by Nodes and Node Objects
# ------------------------------------------------
class CommunicationAgent():

    class _PubSub():
        def __init__(self):
            self.topics = defaultdict(set)

        def subscribe(self, topic, f):
            """
            Subscribe the function/method ``f`` to ``topic``.
            """
            self.topics[topic].add(f)

        def publish(self, topic, **kwargs):
            """
            Publish ``**kwargs`` to ``topic``, calling all functions/methods
            subscribed to ``topic`` with the arguments specified in ``**kwargs``.
            """
            for f in self.topics[topic]:
                f(**kwargs)

    def __init__(self, channel, subscriptions, sim, subscription_callback, parent) -> None:
        self._subscriptions = subscriptions
        self._parent = parent
        self._channel = channel
        self._subscription_callback = subscription_callback
        self._pubsub = self._PubSub()

        for sub_topic in subscriptions:
            topic = channel + "." + sub_topic
            sim.add(self.wait_for_msg, topic)

    def get_subscriptions(self):
        return self._subscription_list

    def publish(self, sub_topic, msg):
        topic = self._channel + "." + sub_topic
        self._pubsub.publish(topic, arg1=msg)

    def wait_for_msg(self, topic):
        current_process = Process.current()

        def receive_msg(arg1, arg2=None):
            print("{0} {1}: Received topic {2} ".format(self._parent._type, self._parent._id, topic))
            current_process.local.msg_data = arg1
            self._subscription_callback(topic, arg1)
            current_process.resume()

        self._pubsub.subscribe(topic, receive_msg)

        while True:
            print("{0} {1}: Waiting for topic {2}".format(self._parent._type, self._parent._id, topic))
            greensim.pause()
            print("{0} {1}: Resuming".format(self._parent._type, self._parent._id, topic))
        # return local.msg_data

class File_DBG(ITObject):

    def __init__(self, sim, parent_node_id) -> None:
        super().__init__()
        self._type = "file"
        self._agent = CommunicationAgent(channel=parent_node_id,
                                         subscriptions=["node.shutdown"],
                                         sim=sim,
                                         subscription_callback=self.subscription_callback,
                                         parent=self)  # replace "FILE" by obj type

    def subscription_callback(self, topic, data):
        if topic.endswith("node.shutdown"):
            print("File has just been notified the parent node shut down: Node UUID: {0}".format(data._id))

    def get_subcriptions(self):
        return self._agent.get_subscriptions()

    def generate_activity(self, activity):
        self._agent.publish(activity, msg=self)


class Node(_Node):
    """
    Machine taking part to a network.
    """

    def __init__(self, sim: Simulator):
        super().__init__()
        self._interfaces: MutableMapping[Cidr, Interface] = OrderedDict()
        self.connected_to(Loopback(), "127.0.0.1")
        self._sockets: MutableMapping[Port, Socket] = OrderedDict()
        self._cycle_ports_ephemeral = cycle(range(PORT_EPHEMERAL_MIN, PORT_EPHEMERAL_UPPER))

        self._proc_set: Set[Process] = set()
        self._process_counter: int = 0
        self._default_process_parent = Process(-1, self)

        self._sim = sim
        self._sim.graph.add_node(str(self._uuid))
        self._subscriptions = [
            "file.open",
            "file.close",
        ]
        self._type = 'node'
        self._files: List[File_DBG] = []  # Debug only
        self._pubsub_agent = CommunicationAgent(channel=str(self._uuid),
                                                subscriptions=self._subscriptions,
                                                sim=self._sim,
                                                subscription_callback=self.pubsub_subscription_callback,
                                                parent=self)

    def pubsub_subscription_callback(self, topic, data):
        if topic.endswith("file.open"):
            self._sim.logger.info("Node has just been notified a file has been opened: File UUID: {0}".format(data._id))

    # TODO: replace this by simply putting "_agent.publish" wherever required
    def generate_activity(self, activity):
        self._pubsub_agent.publish(activity, msg=self)

    # Review how to handle the logger (and logger level)
    def log(self, msg):
        self._sim.logger.info(msg)

    # test function to test the pubsub... (all itobjects belonging to the node should have a CommunicationAgent to
    # handle pubsub to/from the node.
    def create_file_DBG(self):
        new_file = File_DBG(self._sim, str(self._uuid))
        self._files.append(new_file)
        return new_file

    def json(self):
        # TODO: add all usefull node properties to JSON object (and schema)
        return create_json_item(sim_uuid=str(self._sim.uuid),
                                timestamp=now_iso8601(),
                                item_type=self._type,
                                uuid=str(self._uuid),
                                node_label='')



    def connected_to(
        self,
        link: Link,
        ar: AddressRepr = None,
        forwardings: Optional[List[Forwarding]] = None,
        dhcp_with: Optional[Simulator] = None,
        dhcp_delay: float = 0.0
    ) -> "Node":
        """
        Configures a Node to be connected to a given :py:class:`Link`. This thereby adds an
        :py:class:`Interface` to the node.

        :param link:
            Link instance to connect this node to.
        :param ar:
            Optional address to assume as participant to the network embodied by the given link. If this is not
            provided, the address assumed is host number 0 within the CIDR associated to the link.
        :param forwardings:
            List of forwarding rules known by this node in order to exchange packets with other internetworking nodes.
        :param dhcp_with:
            Simulator with which to launch a DHCP client to gather networking information for the link connected to.
        :param dhcp_delay:
            Delay advanced before DHCP client is started. This is mostly useful when instantiating an infra from
            scratch, whereby the server starts at the same time as the client, so as to avoid undue unresponded DISCOVER
            requests at the beginning.

        :return: The node instance, so it can be further built.
        """
        link._connect(self)
        interface = Interface(link, as_address(ar, link.cidr), forwardings or [])
        self._interfaces[link.cidr] = interface

        if dhcp_with is not None:
            self.fork_exec_in(dhcp_with, dhcp_delay, dhcp_client, interface)
        return self

    def addresses(self) -> Iterator[Address]:
        """
        Iterator through the IP addresses assumed by this node.
        """
        return (interface.address for interface in self.interfaces())

    def interfaces(self) -> Iterator[Interface]:
        """
        Iterator through the networking interfaces set up for this node.
        """
        yield from self._interfaces.values()

    def _get_port_ephemeral(self) -> Port:
        num_ports_visited = 0
        for port in self._cycle_ports_ephemeral:
            if self.is_port_free(port):
                return port
            num_ports_visited += 1
            if num_ports_visited >= NUM_PORTS_EPHEMERAL:
                break
        raise EphemeralPortsAllInUse()

    def bind(self, pr: PortRepr = 0, as_pid: int = -1) -> Socket:
        """
        Reserves networking resources, in particular a port, for a calling process. If no port is provided, or port 0,
        then a random free port is thus bound. The binding is embedded in a :py:class:`Socket` instance which may be
        then used to send and receive packets of information.

        :param pr:
            Optional port to bind.
        :param as_pid:
            Optional ID of process flagging itself as owner of the socket.

        :return:
            The :py:class:`Socket` instance suitable for sending packets (using the bound port as source) and receiving
            packets (against the bound port).
        """
        port = as_port(pr) or self._get_port_ephemeral()
        if not self.is_port_free(port):
            raise PortAlreadyInUse(port)
        socket = Socket(port, self, as_pid)
        self._sockets[port] = socket
        return socket

    def is_port_free(self, port: PortRepr) -> bool:
        """
        Tells whether the given port number is free, and thus can be used with :py:meth:`bind`.
        """
        return port not in [PORT_NULL, PORT_MAX] and port not in self._sockets

    def _deallocate_socket(self, socket: Socket) -> None:
        del self._sockets[socket.port]

    def _solve_transfer(self, address_dest: Address) -> Tuple[Interface, Address]:
        interface_best = None
        forwarding_best = None
        for interface in self.interfaces():
            for forwarding in interface.forwardings:
                if address_dest in forwarding.cidr:
                    if forwarding_best is None or forwarding.cidr.prefixlen > forwarding_best.cidr.prefixlen:
                        forwarding_best = forwarding
                        interface_best = interface

        if forwarding_best is None:
            raise NoRouteToHost(address_dest)

        return cast(Interface, interface_best), cast(Forwarding, forwarding_best).get_hop(address_dest)

    def _send_packet(self, port_source: int, dest: Location, num_bytes: int, payload: Payload) -> None:
        interface, address_hop = self._solve_transfer(dest.hostname_as_address())
        packet = Packet(Location(interface.address, port_source), dest, num_bytes, payload)
        interface.link._transfer_packet(packet, address_hop)

    def _receive_packet(self, packet: Packet) -> None:
        address_dest = packet.dest.hostname_as_address()
        if any(
            interface.address == address_dest or interface.cidr.broadcast_address == address_dest
            for interface in self.interfaces()
        ):
            if packet.dest.port in self._sockets:
                self._sockets[packet.dest.port]._enqueue(packet)
            else:
                self.drop_packet(packet)
        else:
            self.handle_packet_transit(packet)

    def handle_packet_transit(self, packet: Packet) -> None:
        """
        invoked when a packet is delivered to this node that is not addressed to it. The default behaviour is to drop
        the packet.
        """
        self.drop_packet(packet)

    def drop_packet(self, packet: Packet) -> None:
        """
        Invoked when a packet delivered to this node cannot be handled. The default is just to ignore it.
        """
        pass

    def resolve_name(self, hostname: Hostname) -> Address:
        """
        Get a node to resolve the given name to an IP address. For this, the node must have been equipped with a domain
        resolution configuration.

        :param hostname:
            Name to resolve.

        :return:
            IP address the name resolves to for this host. If resolution fails, the :py:class:`NameNotFound` exception
            is raised. If the given hostname is actually an IP address, then it is returned as is.
        """
        try:
            return as_address(hostname)
        except ValueError:
            # TODO -- Implement name resolution.
            raise NotImplementedError()

    def procs(self) -> Set[Process]:
        return self._proc_set

    def fork_exec_in(self, sim: Simulator, time: float, f: Callable[..., None], *args, **kwargs) -> Process:
        proc = Process(self.next_proc_number(), self, self._default_process_parent)
        self._proc_set |= set([proc])
        proc.exc_in(sim, time, f, *args, **kwargs)
        return proc

    def fork_exec(self, sim: Simulator, f: Callable[..., None], *args, **kwargs) -> Process:
        return self.fork_exec_in(sim, 0, f, *args, **kwargs)

    def run_file(self, sim: Simulator, file: File, user: UserAccount) -> None:
        self.fork_exec(sim, file.get_executable(user))

    def next_proc_number(self) -> int:
        self._process_counter += 1
        return self._process_counter - 1

    def proc_exit(self, p: Process) -> None:
        self._proc_set -= set([p])

    def with_proc_at(self, sim: Simulator, time: float, f: Callable[[Thread], None], *args, **kwargs) -> _Node:
        self.fork_exec_in(sim, time, f, *args, **kwargs)
        return self

    def with_files(self, *files: File) -> None:
        pass

    def subscribe_networking_daemon(self,
                                    sim: Simulator,
                                    daemon: Daemon,
                                    protocol: Protocol,
                                    *ports: PortRepr) -> None:
        """
        This method contains the logic subscribing the daemon to network events

        :param sim: Simulator instance.
        :param daemon: The :py:class:`~itsim.machine.process_management.daemon.Daemon` that is subscribing to events
        :param protocol: Member of the :py:class:`~itsim.types.Protocol` enum indicating the protocol of the
            transmissions
        :param ports: Variable number of :py:class:`~itsim.types.PortRepr` objects indicating the ports on which
            to listen

        This method does two things:

        1. Attempts to open a socket at each of the specified ports
        2. Schedules an event in `sim` that will wait for a packet on the socket, and once one is received call the
            `trigger` method on `daemon`. After the packet receipt and before `trigger` is executed a new
            :py:class:`~itsim.machine.process_management.thread.Thread` is opened to wait for another packet in parallel
        """
        def serve_on_port(thread: Thread, port: int):
            with self.bind(port, thread.process.pid) as socket:
                while True:
                    packet = socket.recv()
                    thread.process.exc(sim, daemon.trigger, packet, socket)

        def run_daemon(thread: Thread):
            daemon.running_as(thread)
            for port in ports:
                thread.process.exc(sim, serve_on_port, port)

        self.fork_exec(sim, run_daemon)

    def networking_daemon(self, sim: Simulator, protocol: Protocol, *ports: PortRepr) -> Callable:
        """
        Makes the node run a daemon with custom request handling behaviour.

        :param sim: Simulator instance.
        :param protocol: Member of the :py:class:`~itsim.types.Protocol` enum indicating the protocol of the
            transmissions
        :param ports: Variable number of :py:class:`~itsim.types.PortRepr` objects indicating the ports on which
            to listen

        This routine is meant to be used as a decorator over either a class, or some other callable. In the case of a
        class, it must subclass the `Daemon` class, have a constructor which takes no arguemnts,
        and implement the service's discrete event logic by overriding the
        methods of this class. This grants the most control over connection acceptance behaviour and client handling.
        In the case of some other callable, such as a function, it is expected to handle this invocation prototype::

            def handle_request(thread: :py:class:`~itsim.machine.process_management.thread.Thread`,
                packet: :py:class:`~itsim.network.packet.Packet`,
                socket: :py:class:`~itsim.machine.node.Socket`) -> None

        The daemon instance will run client connections acceptance. The resulting socket will be forwarded to the
        callable input to the decorator.
        """
        def _decorator(server_behaviour: Union[Callable, Daemon]) -> Union[Callable, Daemon]:
            daemon = None
            if hasattr(server_behaviour, "trigger"):
                if isinstance(server_behaviour, Daemon):
                    daemon = cast(Daemon, server_behaviour)
                else:
                    daemon = cast(Daemon, server_behaviour())
            elif hasattr(server_behaviour, "__call__"):
                daemon = Daemon(cast(Callable, server_behaviour))
            else:
                raise TypeError("Daemon must have trigger() or be of type Callable")
            self.subscribe_networking_daemon(sim, daemon, protocol, *ports)
            return server_behaviour

        return _decorator

    def __str__(self):
        return f"{type(self).__name__}({', '.join(str(address) for address in self.addresses())})"

    def __repr__(self):
        return str(self)
