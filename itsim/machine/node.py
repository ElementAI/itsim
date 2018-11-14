from collections import OrderedDict
from queue import Queue
from typing import Callable, Generator, MutableMapping, Optional, Set, Iterator, List, cast

import greensim
from greensim.random import project_int, uniform

from itsim import _Node
from itsim import ITObject
from itsim.network.connection import Connection
from itsim.network.forwarding import Forwarding
from itsim.network.interface import Interface
from itsim.network.link import Link, Loopback
from itsim.network.location import Location, LocationRepr
from itsim.network.packet import Payload, Packet
from itsim.machine.file_system import File
from itsim.machine.process_management import _Daemon
from itsim.machine.process_management.process import Process
from itsim.machine.process_management.thread import Thread
from itsim.machine.user_management import UserAccount
from itsim.simulator import Simulator
from itsim.types import Address, AddressRepr, Port, PortRepr, Hostname, as_address, Cidr, as_port, Protocol


MapPorts = MutableMapping[Port, Process]


class _DestinationError(Exception):

    def __init__(self, dest: Address) -> None:
        super().__init__()
        self.dest = dest


class NoSuitableSourceAddress(_DestinationError):
    pass


class NameNotFound(Exception):

    def __init__(self, name: Hostname) -> None:
        super().__init__()
        self.name = name


class Socket(ITObject):

    def __init__(self, port: Port, node: _Node) -> None:
        super().__init__()
        self._is_closed = False
        self._port = port
        self._node = node
        self._packet_queue: Queue[Packet] = Queue()
        self._packet_signal: greensim.Signal = greensim.Signal().turn_off()

    @property
    def port(self):
        if self.is_closed:
            raise ValueError("Socket is closed")
        return self._port

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> bool:
        self.close()
        return False

    def close(self) -> None:
        self._node._close_socket(self.port)
        self._is_closed = True

    @property
    def is_closed(self) -> bool:
        return self._is_closed

    def send(self, dr: LocationRepr, size: int, payload: Optional[Payload] = None) -> None:
        if self.is_closed:
            raise ValueError("Socket is closed")
        dest = Location.from_repr(dr)
        address_dest = self._resolve_destination_final(dest.hostname)
        self._node._send_packet(
            Packet(Location(None, self.port), Location(address_dest, dest.port), size, payload)
        )

    def _resolve_destination_final(self, hostname_dest: Hostname) -> Address:
        try:
            return as_address(hostname_dest)
        except ValueError:
            return self._node.resolve_name(hostname_dest)

    def _enqueue(self, packet: Packet) -> None:
        self._packet_queue.put(packet)
        self._packet_signal.turn_on()

    def recv(self) -> Packet:
        if self.is_closed:
            raise ValueError("Socket is closed")

        self._packet_signal.wait()
        output = self._packet_queue.get()
        if self._packet_queue.empty():
            self._packet_signal.turn_off()

        return output


class PortAlreadyInUse(Exception):

    def __init__(self, port: Port) -> None:
        super().__init__()
        self.port = port


class Node(_Node):

    def __init__(self):
        super().__init__()
        self._interfaces: MutableMapping[Cidr, Interface] = OrderedDict()
        self.connected_to(Loopback(), "127.0.0.1")
        self._sockets: MutableMapping[Port, Socket] = OrderedDict()
        self._unprivileged_port = project_int(uniform(1024, 65536))

        self._proc_set: Set[Process] = set()
        self._process_counter: int = 0
        self._default_process_parent = Process(-1, self)
        self._port_table: MutableMapping[Port, Connection] = OrderedDict()

    def connected_to(self, link: Link, ar: AddressRepr = None, forwardings: Optional[List[Forwarding]] = None) -> "Node":
        """
        Configures a budding node to be connected to a given link.

        :return: The node instance, so it can be further built.
        """
        link._connect(self)
        interface = Interface(link, as_address(ar, link.cidr), forwardings or [])
        self._interfaces[link.cidr] = interface

        # TODO -- Decide whether to set up DHCP client for this interface
        return self

    def addresses(self) -> Iterator[Address]:
        return (interface.address for interface in self.interfaces())

    def interfaces(self) -> Iterator[Interface]:
        yield from self._interfaces.values()

    # def get_address_neighbour(self, neighbour: Address) -> Address:
    #     """
    #     Gives the first address this node bears that is part of the same network as the given address.
    #     """
    #     for interface in self.interfaces():
    #         if neighbour in interface.cidr:
    #             return interface.address
    #     raise NotNeighbouring(neighbour)

    # def iter_addresses_with_gateway(self, address_dest: Address) -> Generator[Address, None, None]:
    #     for interface in self.interfaces():
    #         if interface.has_gateway:
    #             yield interface.address

    def _sample_port_unprivileged_free(self) -> Port:
        while True:
            port = cast(Port, next(self._unprivileged_port))
            if self.is_port_free(port):
                return port

    def bind(self, pr: PortRepr = 0) -> Socket:
        port = as_port(pr) or self._sample_port_unprivileged_free()
        if port in self._sockets:
            raise PortAlreadyInUse(port)
        socket = Socket(port, self)
        self._sockets[port] = socket
        return socket

    def is_port_free(self, port: PortRepr) -> bool:
        return port not in [0, 65535] and port not in self._sockets

    def _close_socket(self, port: Port) -> None:
        del self._sockets[port]

    def _send_packet(self, packet: Packet) -> None:
        raise NotImplementedError()

    def _receive_packet(self, packet: Packet) -> None:
        raise NotImplementedError()

    def resolve_name(self, hostname: Hostname) -> Address:
        raise NotImplementedError()

    def procs(self) -> Set[Process]:
        return self._proc_set

    def fork_exec_in(self, sim: Simulator, time: float, f: Callable[[Thread], None], *args, **kwargs) -> Process:
        proc = Process(self.next_proc_number(), self, self._default_process_parent)
        self._proc_set |= set([proc])
        proc.exc_in(sim, time, f, *args, **kwargs)
        return proc

    def fork_exec(self, sim: Simulator, f: Callable[[Thread], None], *args, **kwargs) -> Process:
        return self.fork_exec_in(sim, 0, f, *args, **kwargs)

    def run_file(self, sim: Simulator, file: File, user: UserAccount) -> None:
        self.fork_exec(sim, file.get_executable(user))

    def next_proc_number(self) -> int:
        self._process_counter += 1
        return self._process_counter - 1

    def proc_exit(self, p: Process) -> None:
        self._proc_set -= set([p])
        print("Remaining Procs: %s" % ", ".join([str(pro.__hash__()) for pro in self._proc_set]))

    def with_proc_at(self, sim: Simulator, time: float, f: Callable[[Thread], None], *args, **kwargs) -> _Node:
        self.fork_exec_in(sim, time, f, *args, **kwargs)
        return self

    def with_files(self, *files: File) -> None:
        pass

    def subscribe_daemon(self, daemon: _Daemon, protocol: Protocol, *ports: PortRepr) -> None:
        """
        This method will eventually contain logic subscribing the daemon to relevant events.

        It should be based on the PubSub functionality in https://github.com/ElementAI/itsim_private/pull/32
        """
        # TODO This behavior is not well-defined. Accessing this table should allow the packet to be
        # passed to whichever entity is designated to manage it
        for port in ports:
            self._port_table[as_port(port)] = Connection()
