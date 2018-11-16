from collections import OrderedDict
from itertools import cycle
from queue import Queue
from typing import Callable, MutableMapping, Optional, Set, Iterator, List

import greensim

from itsim import _Node
from itsim import ITObject
from itsim.network.forwarding import Forwarding
from itsim.network.interface import Interface
from itsim.network.link import Link, Loopback
from itsim.network.location import Location, LocationRepr
from itsim.network.packet import Payload, Packet
from itsim.machine.file_system.__init__ import File
from itsim.machine.process_management.__init__ import _Daemon
from itsim.machine.process_management.process import Process
from itsim.machine.process_management.thread import Thread
from itsim.machine.user_management.__init__ import UserAccount
from itsim.simulator import Simulator
from itsim.types import Address, AddressRepr, Port, PortRepr, Hostname, as_address, Cidr, as_port, Protocol


PORT_EPHEMERAL_MIN = 32768
PORT_EPHEMERAL_UPPER = 61000
NUM_PORTS_EPHEMERAL = PORT_EPHEMERAL_UPPER - PORT_EPHEMERAL_MIN


MapPorts = MutableMapping[Port, Process]


class NameNotFound(Exception):
    """
    Raised when a domain name cannot be resolved to an IP address.
    """

    def __init__(self, name: Hostname) -> None:
        super().__init__()
        self.name = name


class Timeout(Exception):
    """
    Raised when the reception of a :py:class:`Packet` through a :py:class:`Socket` times out.
    """
    pass


class Socket(ITObject):
    """
    Resource reserved for a :py:class:`Process` running on a :py:class:`Node` to send and receive packets on the
    networks the node is connected to. This class is not instantiated directly, but rather obtained as result of the method
    :py:meth:`Node.bind`.

    The preferred way to handle a socket is to use it as a context manager (``with`` statement). Exiting the context
    will trigger the :py:meth:`close`'ing of the socket. Otherwise, the user must take care to invoke this method,
    otherwise the resources on the associated :py:class:`Node` will stay associated to the socket even once it goes out
    of scope.

    :param port:
        Port reserved on the host for running network transactions.
    :param node:
        Node that instantiated this object.
    """

    def __init__(self, port: Port, node: _Node) -> None:
        super().__init__()
        self._is_closed = False
        self._port = port
        self._node = node
        self._packet_queue: Queue[Packet] = Queue()
        self._packet_signal: greensim.Signal = greensim.Signal().turn_off()

    @property
    def port(self):
        """
        Port reserved by this socket on the :py:class:`Node`.
        """
        if self.is_closed:
            raise ValueError("Socket is closed")
        return self._port

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> bool:
        self.close()
        return False

    def close(self) -> None:
        """
        Closes the socket, relinquishing the resources it reserves on the :py:class:`Node` that instantiated it.
        """
        self._node._deallocate_socket(self.port)
        self._is_closed = True
        self._packet_signal.turn_on()

    @property
    def is_closed(self) -> bool:
        """
        Tells whether the socket has been closed.
        """
        return self._is_closed

    def send(self, dr: LocationRepr, size: int, payload: Optional[Payload] = None) -> None:
        """
        Sends information to a certain destination, in the form of a :py:class:`Packet`. The source address of the
        packet will be determined depending on its destination.

        :param dr:
            Destination of the packet, either provided as a :py:class:`Location` instance or as a (hostname, port)
            tuple.
        :param size:
            Number of bytes to send.
        :param payload:
            Optional information payload added to the :py:class:`Packet` instance, which may be useful for simulating
            the server-side part of the transaction or session.
        """
        if self.is_closed:
            raise ValueError("Socket is closed")
        dest = Location.from_repr(dr)
        address_dest = self._node.resolve_name(dest.hostname)
        self._node._send_packet(
            Packet(Location(None, self.port), Location(address_dest, dest.port), size, payload)
        )

    def _enqueue(self, packet: Packet) -> None:
        self._packet_queue.put(packet)
        self._packet_signal.turn_on()

    def recv(self, timeout: Optional[float] = None) -> Packet:
        """
        Blocks until a packet is received on the socket's :py:meth:`port`.

        :param timeout:
            If this parameter is set to a numerical value, the process invoking this method only blocks this much time.
            If no packet is received when the timeout fires, the :py:class:`Timeout` exception is raised on the calling
            process.
        """
        if self.is_closed:
            raise ValueError("Socket is closed")

        try:
            self._packet_signal.wait(timeout)
        except greensim.Timeout:
            raise Timeout()

        if self.is_closed:
            raise ValueError("Socket is closed")
        output = self._packet_queue.get()
        if self._packet_queue.empty():
            self._packet_signal.turn_off()

        return output


class PortAlreadyInUse(Exception):
    """
    Raised when attempting to :py:meth:`Node.bind` a socket that is already bound and for which the :py:class:`Socket`
    has not yet been :py:meth:`Socket.close`'d.
    """

    def __init__(self, port: Port) -> None:
        super().__init__()
        self.port = port


class Node(_Node):
    """
    Machine taking part to a network.
    """

    def __init__(self):
        super().__init__()
        self._interfaces: MutableMapping[Cidr, Interface] = OrderedDict()
        self.connected_to(Loopback(), "127.0.0.1")
        self._sockets: MutableMapping[Port, Socket] = OrderedDict()
        self._cycle_ports_ephemeral = cycle(range(PORT_EPHEMERAL_MIN, PORT_EPHEMERAL_UPPER))

        self._proc_set: Set[Process] = set()
        self._process_counter: int = 0
        self._default_process_parent = Process(-1, self)

    def connected_to(
        self,
        link: Link,
        ar: AddressRepr = None,
        forwardings: Optional[List[Forwarding]] = None
    ) -> "Node":
        """
        Configures a budding node to be connected to a given :py:class:`Link`. This thereby adds an
        :py:class:`Interface` to the node.

        :param link:
            Link instance to connect this node to.
        :param ar:
            Optional address to assume as participant to the network embodied by the given link. If this is not
            provided, the address assumed is 0.0.0.0.
        :param forwardings:
            List of forwarding rules known by this node in order to exchange packets with other internetworking nodes.

        :return: The node instance, so it can be further built.
        """
        link._connect(self)
        interface = Interface(link, as_address(ar, link.cidr), forwardings or [])
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
        raise RuntimeError("No ephemeral port left to allocate.")

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
        self._sockets[port] = socket
        return socket

    def is_port_free(self, port: PortRepr) -> bool:
        """
        Tells whether the given port number is free, and thus can be used with :py:meth:`bind`.
        """
        return port not in [0, 65535] and port not in self._sockets

    def _deallocate_socket(self, port: Port) -> None:
        del self._sockets[port]

    def _send_packet(self, packet: Packet) -> None:
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
                                    daemon: _Daemon,
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

    def __str__(self):
        return "(%s)" % ", ".join([str(i) for i in [
            self._interfaces,
            self._sockets,
            self._proc_set,
            self._process_counter,
            self._default_process_parent,
        ]])
