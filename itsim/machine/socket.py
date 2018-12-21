from datetime import timedelta
from queue import Queue
from typing import Optional, cast
from uuid import uuid4, UUID

import greensim
from itsim.datastore.datastore import DatastoreClientFactory, DatastoreClient
from itsim.machine.__init__ import _Socket, _Node
from itsim.network.location import LocationRepr, Location
from itsim.network.packet import Packet
from itsim.schemas.items import create_json_network_event
from itsim.simulator import now, get_tags
from itsim.types import Port, Address, as_address, Payload, Hostname, Protocol, is_ip_address, Timeout


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
        self._port = port
        self._protocol = protocol
        self._node: _Node = node
        self._pid: int = pid
        self._packet_queue: Queue[Packet] = Queue()
        self._packet_signal: greensim.Signal = greensim.Signal().turn_off()
        self._close_signal: greensim.Signal = greensim.Signal().turn_off()
        self._num_bytes_sent = 0
        self._num_bytes_received = 0
        factory = DatastoreClientFactory()
        self._sim_uuid = factory.sim_uuid
        self._time_start = factory.time_start
        self._client_ds: Optional[DatastoreClient] = factory.get_client()
        self._record("open", None, None)

    def _record(self, network_event_type: str, address_src: Optional[Address], dest: Optional[Location]) -> None:
        if self._client_ds is not None:
            self._client_ds.store_item(
                create_json_network_event(
                    sim_uuid=cast(UUID, self._sim_uuid),
                    timestamp=(self._time_start + timedelta(0, now())).isoformat(),
                    uuid=uuid4(),
                    tags=[tag.name for tag in get_tags()],
                    uuid_node=self._node.uuid,
                    network_event_type=network_event_type,
                    protocol=str(self.protocol),
                    pid=self._pid,
                    src=(str(address_src) if address_src is not None else "", self.port),
                    dst=(str(dest.hostname), dest.port) if dest is not None else ("", 0)
                )
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

    def __del__(self):
        """
        This is a safeguard against failure to properly close a socket before its reference is dropped. As a
        :py:class:`Node` instance reserves the port associated to this socket, failure to close would leak the port.
        Thus, the :py:class:`Node` that instantiated this socket through :py:meth:`Socket.bind` only keeps a weak
        reference to it; when the owner drops the reference to the socket, it can thus be finalized, and the port can be
        safely reclaimed.
        """
        self.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> bool:
        self.close()
        return False

    def close(self) -> None:
        """
        Closes the socket, relinquishing the resources it reserves on the :py:class:`Node` that instantiated it.
        """
        if not self.is_closed:
            self._record("close", None, None)
            self._node._deallocate_socket(self)
            self._close_signal.turn_on()

    @property
    def is_closed(self) -> bool:
        """
        Tells whether the socket has been closed.
        """
        return self._close_signal.is_on

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
        address_dest = self._resolve_destination(dest.hostname)
        dest_resolved = Location(address_dest, dest.port)
        address_src = self._node._send_packet(self.port, dest_resolved, size, payload or {})
        self._record("send", address_src, dest_resolved)

    def _resolve_destination(self, hostname_dest: Hostname) -> Address:
        if is_ip_address(hostname_dest):
            return as_address(hostname_dest)
        else:
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
            greensim.select(self._packet_signal, self._close_signal, timeout=timeout)
        except greensim.Timeout:
            raise Timeout()

        if self.is_closed:  # Only possible if the close signal has been turned on.
            raise ValueError("Socket is closed")

        output = self._packet_queue.get()
        if self._packet_queue.empty():
            self._packet_signal.turn_off()

        self._record("recv", output.dest.hostname_as_address(), output.source)
        return output
