from collections import OrderedDict
from contextlib import contextmanager
from ipaddress import _BaseAddress
from queue import Queue
from typing import Callable, cast, Generator, Iterable, MutableMapping, Optional, Set, Tuple, TypeVar

import greensim

from ipaddress import ip_address

from itsim import _Node
from itsim import ITObject
from itsim.network.link import Link
from itsim.network.location import AddressInUse, InvalidAddress, Location
from itsim.network.packet import Payload, Packet
from itsim.node.accounts import UserAccount
from itsim.node.files import File
from itsim.node.processes.process import Process
from itsim.node.processes.thread import Thread
from itsim.simulator import Simulator
from itsim.types import Address, AddressRepr, Port, PortRepr


MapPorts = MutableMapping[Port, Process]


class Socket(ITObject):

    def __init__(self, src: Location, node: _Node) -> None:
        super().__init__()
        self._src = src
        self._node = node
        self._packet_queue: Queue[Packet] = Queue()
        self._packet_signal: greensim.Signal = greensim.Signal()
        self._packet_signal.turn_off()

    def send(self, dest: Location, byte_size: int, payload: Payload) -> None:
        ob_packet = Packet(self._src, dest, byte_size, payload)
        self._node._send_to_network(ob_packet)

    # Placeholder method
    def broadcast(self, port: int, byte_size: int, payload: Payload) -> None:
        """
        This method is currently a placeholder under active development
        """
        pass

    def _enqueue(self, packet: Packet) -> None:
        self._packet_queue.put(packet)
        self._packet_signal.turn_on()

    def recv(self) -> Packet:
        # Waiting loop
        while self._packet_queue.empty():
            self._packet_signal.wait()

        # Make sure to update the Signal in case more Processes are in the Signal's queue
        output = self._packet_queue.get()

        if self._packet_queue.empty():
            self._packet_signal.turn_off()
        return output


class Host(object):

    def __init__(self):
        raise NotImplementedError()


class Node(_Node):

    LocationBind = TypeVar("LocationBind", AddressRepr, PortRepr, Location, Tuple)

    def __init__(self):
        super().__init__()
        self._address_default: Optional[Address] = None
        self._sockets: MutableMapping[Location, Socket] = OrderedDict()
        self._links: MutableMapping[AddressRepr, Link] = OrderedDict()
        self._proc_set: Set[Process] = set()
        self._process_counter: int = 0
        self._default_process_parent = Process(-1, self)

    def connected_to(self, link: Link) -> "Node":
        """
        Configures a budding node to be connected to a given link.

        :return: The node instance, so it can be further built.
        """
        raise NotImplementedError()
        return self

    def add_physical_link(self, link: Link, ar: AddressRepr) -> None:
        """
        Attempt to connect this Node to the given Link at the given AddressRepr.
        If the AddressRepr is already being used to point to a Link, this will throw AddressInUse.
        Otherwise, it will call add_node on the Link (which in turn will call as_address from itsim.types
        on the AddressRepr) and if the call succeeds this method will store a reference
        to the Link internally at the AddressRepr
        """

        if ar in self._links:
            raise AddressInUse(ar)

        link.add_node(self, ar)

        self._links[ar] = link

    def remove_physical_link(self, ar: AddressRepr) -> bool:
        """
        Attempt to drop the Link that is connected at the given AddressRepr.
        If there is no known Link at the AddressRepr, this method will return False.
        Otherwise, it will free up the AddressRepr for another Node and call drop_node
        on the Link that was previously stored there, returning its result
        """

        if ar not in self._links:
            return False

        link = self._links[ar]
        del self._links[ar]
        return link.drop_node(ar)

    @property
    def addresses(self) -> Iterable[Address]:
        """
        This method is currently a placeholder under active development
        """
        return []

    @property
    def address_default(self) -> Address:
        """
        This method is currently a placeholder under active development
        """
        return ip_address('127.0.0.1')

    def _as_location(self, lb: Optional[LocationBind] = None) -> Location:
        if lb is None:
            return Location(self.address_default, 0)
        elif isinstance(lb, int):
            return Location(self.address_default, cast(Port, lb))
        elif isinstance(lb, (str, _BaseAddress)):
            return Location(cast(AddressRepr, lb), 0)
        elif isinstance(lb, tuple):
            return Location(lb[0], lb[1])
        elif isinstance(lb, Location):
            return cast(Location, lb)
        raise ValueError("What is that LocationBind instance?")

    def _as_source_bind(self, lb: Optional[LocationBind] = None) -> Location:
        loc = self._as_location(lb)  # type: ignore

        # Address here must be one of the node's addresses.
        if not isinstance(loc.hostname, _BaseAddress) or loc.hostname not in self.addresses:
            raise InvalidAddress(loc.hostname)
        elif loc.hostname not in self.addresses:
            raise InvalidAddress(loc.hostname)
        else:
            address = loc.hostname

        port: Port = loc.port

        return Location(address, port)

    # Placeholder method
    @contextmanager
    def bind(self, lb: Optional[LocationBind] = None) -> Generator[Location, None, None]:
        """
        This method is currently a placeholder under active development
        """
        try:
            yield self._as_source_bind(lb)  # type: ignore
        finally:
            # Placeholder for cleanup
            pass

    # Placeholder method
    @contextmanager
    def open_socket(self, lb: Optional[LocationBind] = None) -> Generator[Socket, None, None]:
        """
        This method is currently a placeholder under active development
        """
        with self.bind(lb) as src:  # type: ignore
            try:
                yield Socket(src, self)
            finally:
                # Placeholder for cleanup
                pass

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


class _DefaultAddressSetter(object):

    def __init__(self, node: Node, address: Address) -> None:
        super().__init__()
        self._node = node
        self._address = address

    def set_default(self) -> None:
        self._node._address_default = self._address
