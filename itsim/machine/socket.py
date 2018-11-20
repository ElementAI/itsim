from queue import Queue
from typing import Optional

import greensim
from itsim.machine.__init__ import _Socket, _Node
from itsim.network.location import LocationRepr, Location
from itsim.network.packet import Packet
from itsim.simulator import record
from itsim.types import Port, Address, as_address, Payload, Hostname, Protocol


class Timeout(Exception):
    """
    Raised when the reception of a :py:class:`Packet` through a :py:class:`Socket` times out.
    """
    pass


class Socket(_Socket):
    """
    Resource reserved for a :py:class:`Process` running on a :py:class:`Node` to send and receive packets on the
    networks the node is connected to. This class is not instantiated directly, but rather obtained as result of method
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

    def __init__(self, protocol: Protocol, port: Port, node: _Node, pid: int = -1) -> None:
        super().__init__()
        self._is_closed = False
        self._port = port
        self._protocol = protocol
        self._node: _Node = node
        self._pid: int = pid
        self._packet_queue: Queue[Packet] = Queue()
        self._packet_signal: greensim.Signal = greensim.Signal().turn_off()
        self._num_bytes_sent = 0
        self._num_bytes_received = 0
        self._last_dest = Location()
        self._record("open")

    def _record(self, network_item_type: str) -> None:
        record(
            item_type="network_event",
            network_item_type=network_item_type,
            uuid_node=self._node.uuid,
            protocol=self.protocol.name,
            src=["", self.port],
            dest=[self._last_dest.hostname_as_address(), self._last_dest.port]
        )

    @property
    def protocol(self) -> Protocol:
        if self.is_closed:
            raise ValueError("Socket is closed")
        return self._protocol

    @property
    def port(self) -> Port:
        """
        Port reserved by this socket on the :py:class:`Node`.
        """
        if self.is_closed:
            raise ValueError("Socket is closed")
        return self._port

    @property
    def pid(self) -> int:
        if self.is_closed:
            raise ValueError("Socket is closed")
        return self._pid

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> bool:
        self.close()
        return False

    def close(self) -> None:
        """
        Closes the socket, relinquishing the resources it reserves on the :py:class:`Node` that instantiated it.
        """
        self._record("close")
        self._node._deallocate_socket(self)
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
        address_dest = self._resolve_destination_final(dest.hostname)
        self._last_dest = Location(address_dest, dest.port)
        self._node._send_packet(self.port, self._last_dest, size, payload or {})

    def _resolve_destination_final(self, hostname_dest: Hostname) -> Address:
        try:
            return as_address(hostname_dest)
        except ValueError:
            return self._node.resolve_name(hostname_dest)

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
