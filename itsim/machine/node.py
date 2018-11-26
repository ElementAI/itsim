from .__init__ import _Node

from collections import OrderedDict
from itertools import cycle
from typing import Callable, cast, Iterator, List, MutableMapping, Optional, Set, Union
import weakref

from itsim.network.route import Route
from itsim.network.interface import Interface
from itsim.network.link import Link, Loopback
from itsim.network.location import Location
from itsim.network.packet import Payload, Packet
from itsim.machine.file_system import File
from itsim.machine.process_management.daemon import Daemon
from itsim.machine.process_management.process import Process
from itsim.machine.process_management.thread import Thread
from itsim.machine.socket import Socket
from itsim.machine.user_management.__init__ import UserAccount
from itsim.simulator import Simulator
from itsim.types import Address, AddressRepr, as_address, as_port, Cidr, Hostname, Port, PortRepr, Protocol, \
    is_ip_address

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


class Node(_Node):
    """
    Machine taking part to a network.
    """

    def __init__(self):
        super().__init__()
        self._interfaces: MutableMapping[Cidr, Interface] = OrderedDict()
        self.connected_to(Loopback(), "127.0.0.1")
        self._sockets: MutableMapping[Port, weakref.ReferenceType] = OrderedDict()
        self._cycle_ports_ephemeral = cycle(range(PORT_EPHEMERAL_MIN, PORT_EPHEMERAL_UPPER))

        self._proc_set: Set[Process] = set()
        self._process_counter: int = 0
        self._default_process_parent = Process(-1, self)

    def connected_to(
        self,
        link: Link,
        ar: AddressRepr = None,
        routes: Optional[List[Route]] = None
    ) -> "Node":
        """
        Configures a Node to be connected to a given :py:class:`Link`. This thereby adds an
        :py:class:`Interface` to the node.

        :param link:
            Link instance to connect this node to.
        :param ar:
            Optional address to assume as participant to the network embodied by the given link. If this is not
            provided, the address assumed is 0.0.0.0.
        :param routes:
            List of routes known by this node in order to exchange packets with other internetworking nodes.

        :return: The node instance, so it can be further built.
        """
        link._connect(self)
        interface = Interface(link, as_address(ar, link.cidr), routes or [])
        self._interfaces[link.cidr] = interface

        # TODO -- Decide whether to set up DHCP client for this interface
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

    def bind(self, pr: PortRepr = 0) -> Socket:
        """
        Reserves networking resources, in particular a port, for a calling process. If no port is provided, or port 0,
        then a random free port is thus bound. The binding is embedded in a :py:class:`Socket` instance which may be
        then used to send and receive packets of information.

        :param pr:
            Optional port to bind.

        :return:
            The :py:class:`Socket` instance suitable for sending packets (using the bound port as source) and receiving
            packets (against the bound port).
        """
        port = as_port(pr) or self._get_port_ephemeral()
        if not self.is_port_free(port):
            raise PortAlreadyInUse(port)
        socket = Socket(port, self)
        self._sockets[port] = weakref.ref(socket)
        return socket

    def is_port_free(self, port: PortRepr) -> bool:
        """
        Tells whether the given port number is free, and thus can be used with :py:meth:`bind`.
        """
        return port not in [PORT_NULL, PORT_MAX] and port not in self._sockets

    def _deallocate_socket(self, socket: Socket) -> None:
        if socket.port in self._sockets:
            del self._sockets[socket.port]

    def _send_packet(self, port_source: int, dest: Location, num_bytes: int, payload: Payload) -> None:
        raise NotImplementedError()

    def _receive_packet(self, packet: Packet) -> None:
        raise NotImplementedError()

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
        if is_ip_address(hostname):
            return as_address(hostname)
        else:
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
        for port in ports:
            new_sock = self.bind(port)

            def forward_recv(thread: Thread, socket: Socket):
                pack = socket.recv()
                thread._process.exc(sim, forward_recv, socket)
                daemon.trigger(thread, pack, socket)

            self.fork_exec(sim, forward_recv, new_sock)

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
        return "(%s)" % ", ".join([str(i) for i in [
            self._interfaces,
            self._sockets,
            self._proc_set,
            self._process_counter,
            self._default_process_parent,
        ]])
