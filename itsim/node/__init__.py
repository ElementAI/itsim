import json
import logging
import sys
from greensim.logging import Filter

from collections import OrderedDict
from contextlib import contextmanager
from ipaddress import _BaseAddress
from itertools import cycle
from queue import Queue
from typing import Any, Callable, cast, Generator, Iterable, Optional, MutableMapping, List, Set, Tuple, Union

import greensim

from itsim import _Node
from itsim.it_objects import ITObject, Simulator
from itsim.it_objects.location import Location
from itsim.it_objects.networking import _Link
from itsim.it_objects.networking.link import AddressError, AddressInUse, InvalidAddress
from itsim.it_objects.payload import Payload, PayloadDictionaryType
from itsim.it_objects.packet import Packet
from itsim.network import Network
from itsim.node.processes.process import Process
from itsim.node.processes.thread import Thread
from itsim.types import AddressRepr, Address, CidrRepr, as_address, Port, PortRepr


MapPorts = MutableMapping[Port, Process]


class AddressHasPortsOpen(AddressError):

    def __init__(self, address: Any, ports: List[Port]) -> None:
        super.__init__(address)
        self.ports = ports


class NoNetworkLinked(Exception):
    pass


class TooManyPorts(AddressError):
    pass


class PortAlreadyInUse(Exception):
    pass


class _NetworkLink(object):

    def __init__(self, address: Address, network: Network) -> None:
        super().__init__()
        self.address = address
        self.network = network
        self.ports: MapPorts = OrderedDict()
        self._seq_ports_unprivileged = cycle(range(1024, 65536))

    def get_port_free(self):
        if len(self.ports) >= 60000:
            raise TooManyPorts(self.address)
        for port in self._seq_ports_unprivileged:
            if port not in self.ports:
                return port

    def sever(self) -> None:
        self.network.unlink(self.address)


class Socket(ITObject):

    def __init__(self, src: Location, node: _Node) -> None:
        super().__init__()
        self._src = src
        self._node = node
        self._packet_queue: Queue[Packet] = Queue()
        self._packet_signal: greensim.Signal = greensim.Signal()
        self._packet_signal.turn_off()
        # Keeps track of packets waiting for responses so they can be logged together
        # The float keeps track of the time that the packet was queued up
        # This is not at all the best way to handle this, but as a quick hack it is effective
        self._outbound_packets: MutableMapping[Location, Tuple[Packet, float]] = OrderedDict()
        self._inbound_packets: MutableMapping[Location, Tuple[Packet, float]] = OrderedDict()

    def get_logger(self, name_logger=__name__):
        logger = logging.getLogger(name_logger)
        if len(logger.handlers) == 0:
            logger.setLevel(logging.getLogger().level)
            logger.addFilter(Filter())
            handler = logging.StreamHandler(sys.stdout)
            handler.setFormatter(
                logging.Formatter("JSON-OUT <%(levelname)s> %(sim_time)f [%(sim_process)s] %(message)s"))
            logger.addHandler(handler)
        return logger

    # Designed to keep this hack contained. This allows unit tests without a Simulation to succeed
    def get_time_with_fallback(self):
        try:
            return greensim.now()
        except TypeError:
            return 0

    # Check to see if this packet is in response to another one. If so, log the pair as Inbound
    # If not, check whether this socket is already waiting for a response from the destination host
    # If it is waiting just log the old packet without a response, assuming all new responses are to the latest packet
    # If it is not waiting, queue up the outbound packet so we can log the response together with it
    def correlate_outbound_packet(self, dest: Location, ob_packet: Packet) -> None:
        if dest in self._inbound_packets:
            self.log_pair(self._inbound_packets[dest][0], ob_packet, self._inbound_packets[dest][1], True)
            del self._inbound_packets[dest]
        else:
            if dest in self._outbound_packets:
                self.log_pair(None, self._outbound_packets[dest][0], self._outbound_packets[dest][1], False)
            self._outbound_packets[dest] = (ob_packet, self.get_time_with_fallback())

    # Check to see if this packet is in response to another one. If so, log the pair as Outbound
    # If not, queue up the inbound packet so we can log the response together with it
    # This method is used so that the socket can remain independent of packet creation
    # And also so the hack is contained here in this class
    def correlate_inbound_packet(self, src: Location, ib_packet: Packet) -> None:
        if src in self._outbound_packets:
            self.log_pair(ib_packet, self._outbound_packets[src][0], self._outbound_packets[src][1], False)
            del self._outbound_packets[src]
        else:
            self._inbound_packets[src] = (ib_packet, self.get_time_with_fallback())

    def send(self, dest: Location, byte_size: int, payload: Payload) -> None:
        ob_packet = Packet(self._src, dest, byte_size, payload)
        self._node._send_to_network(ob_packet)
        self.correlate_outbound_packet(dest, ob_packet)

    def broadcast(self, port: int, byte_size: int, payload: Payload) -> None:
        dest_addr = self._node._get_network_broadcast_address(self._src.hostname)
        self.send(Location(dest_addr, port), byte_size, payload)

    def _enqueue(self, packet: Packet) -> None:
        self._packet_queue.put(packet)
        self._packet_signal.turn_on()

    def recv(self) -> Packet:
        # Waiting loop
        while self._packet_queue.empty():
            self._packet_signal.wait()

        # Make sure to update the Signal in case more Processes are in the Signal's queue
        output = self._packet_queue.get()

        self.correlate_inbound_packet(output.source, output)

        if self._packet_queue.empty():
            self._packet_signal.turn_off()
        return output

    # Take 0 - 2 packets and log whatever information is available as a JSON object in the format
    # defined in the Telemetry table
    # This method is just a stand-in so it is not very intelligent
    def log_pair(self,
                 packet_in: Optional[Packet],
                 packet_out: Optional[Packet],
                 start: float,
                 is_inbound: bool) -> None:
        remote_ip = "0"
        if packet_out is not None:
            if PayloadDictionaryType.ADDRESS in packet_out._payload._entries:
                remote_ip = str(cast(Address,
                                     packet_out._payload._entries[PayloadDictionaryType.ADDRESS]))
            else:
                remote_ip = str(packet_out.dest.hostname)

        self.get_logger().info(json.dumps({"Connection_Type": "UDP",
                                           "Local_IP": 0 if packet_in is None else str(packet_in.dest.hostname),
                                           "Local_Port": 0 if packet_in is None else str(packet_in.dest.port),
                                           "Direction": "Inbound" if is_inbound else "Outbound",
                                           "Remote_IP": remote_ip,
                                           "Remote_Port": 0 if packet_out is None else str(packet_out.dest.port),
                                           "Sent_Bytes": 0 if packet_out is None else str(packet_out.byte_size),
                                           "Received_Bytes": 0 if packet_in is None else str(packet_in.byte_size),
                                           "PID": 0,
                                           "Start_Time": start,
                                           "End_Time": self.get_time_with_fallback(),
                                           "Parent_Process_Path": "/home/town",
                                           "Parent_Process_Start_Time": start}))

    # When the socket is closed this method is called to log whatever packets didn't end up
    # being part of a transaction
    def flush_logs(self) -> None:
        for pair in self._outbound_packets.values():
            self.log_pair(None, pair[0], pair[1], False)

        for pair in self._inbound_packets.values():
            self.log_pair(pair[0], None, pair[1], True)


class Host(object):

    def __init__(self):
        raise NotImplementedError()


class Node(_Node):

    LocationBind = Union[None, AddressRepr, PortRepr, Location, Tuple]

    def __init__(self):
        super().__init__()
        self._networks: MutableMapping[Address, _NetworkLink] = OrderedDict()
        self._address_default: Optional[Address] = None
        self._sockets: MutableMapping[Location, Socket] = OrderedDict()
        self._links: MutableMapping[AddressRepr, _Link] = OrderedDict()
        self._proc_set: Set[Process] = set()
        self._process_counter: int = 0
        self._default_process_parent = Process(-1, self)

    def add_physical_link(self, link: _Link, ar: AddressRepr) -> None:
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

    def link_to(self, network: Network, ar: AddressRepr = None, *forward_me: CidrRepr) -> "_DefaultAddressSetter":
        if as_address(ar) in self._networks:
            raise AddressInUse(ar)
        address = network.link(self, ar, *forward_me)
        self._networks[address] = _NetworkLink(address, network)
        return _DefaultAddressSetter(self, address)

    def unlink_from(self, ar: AddressRepr) -> None:
        address = as_address(ar)
        if address in self._networks:
            if len(self._networks[address].ports) > 0:
                raise AddressHasPortsOpen(address, list(self._networks[address].ports.keys()))
            self._networks[address].sever()
            del self._networks[address]

    @property
    def addresses(self) -> Iterable[Address]:
        return self._networks.keys()

    @property
    def address_default(self) -> Address:
        try:
            return next(iter(self._networks.keys()))
        except StopIteration:
            raise NoNetworkLinked()

    def _as_location(self, lb: "Node.LocationBind") -> Location:
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

    def _as_source_bind(self, lb: "Node.LocationBind") -> Location:
        loc = self._as_location(lb)

        # Address here must be one of the node's addresses.
        if not isinstance(loc.hostname, _BaseAddress) or loc.hostname not in self.addresses:
            raise InvalidAddress(loc.hostname)
        elif loc.hostname not in self.addresses:
            raise InvalidAddress(loc.hostname)
        else:
            address = loc.hostname

        port: Port = loc.port
        if port == 0:
            # TODO -- Disambiguate between address 0 (bind all addresses against the port) and a specific binding.
            port = self._networks[address].get_port_free()

        return Location(address, port)

    @contextmanager
    def bind(self, lb: "Node.LocationBind" = None) -> Generator[Location, None, None]:
        src = self._as_source_bind(lb)
        if src.port in self._networks[src.hostname_as_address()].ports.keys():
            raise PortAlreadyInUse()

        self._networks[src.hostname_as_address()].ports[src.port] = greensim.Process.current()
        try:
            yield src
        finally:
            del self._networks[src.hostname_as_address()].ports[src.port]

    @contextmanager
    def open_socket(self, lb: "Node.LocationBind" = None) -> Generator[Socket, None, None]:

        with self.bind(lb) as src:
            sock = Socket(src, self)

            # Listen on the broadcast address
            broadcast_addr = self._get_network_broadcast_address(src.hostname_as_address())
            broadcast = Location(broadcast_addr, src.port)

            self._sockets[src] = sock
            self._sockets[broadcast] = sock
            try:
                yield sock
            finally:
                sock.flush_logs()
                del self._sockets[src]
                del self._sockets[broadcast]

    def _send_to_network(self, packet: Packet) -> None:
        src = packet.source
        if src.hostname_as_address() not in self._networks or \
           src.port not in self._networks[src.hostname_as_address()].ports.keys():
            raise NoNetworkLinked()
        network = self._networks[src.hostname_as_address()].network
        network.transmit(packet)

    def _receive(self, packet: Packet) -> None:
        dest = packet.dest
        if dest in self._sockets.keys():
            self._sockets[dest]._enqueue(packet)

    def _get_network_broadcast_address(self, src_addr: Address) -> Address:
        if src_addr not in self._networks:
            raise NoNetworkLinked()
        network = self._networks[src_addr].network
        return network.address_broadcast

    def procs(self) -> Set[Process]:
        return self._proc_set

    def fork_exec_in(self, sim: Simulator, time: float, f: Callable[[Thread], None], *args, **kwargs) -> Process:
        proc = Process(self.next_proc_number(), self, self._default_process_parent)
        self._proc_set |= set([proc])
        proc.exc_in(sim, time, f, *args, **kwargs)
        return proc

    def fork_exec(self, sim: Simulator, f: Callable[[Thread], None], *args, **kwargs) -> Process:
        return self.fork_exec_in(sim, 0, f, *args, **kwargs)

    def next_proc_number(self) -> int:
        self._process_counter += 1
        return self._process_counter - 1

    def proc_exit(self, p: Process) -> None:
        self._proc_set -= set([p])
        print("Remaining Procs: %s" % ", ".join([str(pro.__hash__()) for pro in self._proc_set]))

    def with_proc_at(self, sim: Simulator, time: float, f: Callable[[Thread], None], *args, **kwargs) -> _Node:
        self.fork_exec_in(sim, time, f, *args, **kwargs)
        return self


class _DefaultAddressSetter(object):

    def __init__(self, node: Node, address: Address) -> None:
        super().__init__()
        self._node = node
        self._address = address

    def set_default(self) -> None:
        self._node._address_default = self._address


class Router(Node):

    def __init__(self, lan: Network, wan: Network) -> None:
        super().__init__()
        raise NotImplementedError()
