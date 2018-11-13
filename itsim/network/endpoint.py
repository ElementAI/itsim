from typing import Callable, cast, Union

from itsim.simulator import Simulator
from itsim.machine.node import Node
from itsim.machine.process_management.daemon import Daemon
from itsim.types import PortRepr, Protocol


class Endpoint(Node):
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
                daemon = cast(Daemon, server_behaviour())
            elif hasattr(server_behaviour, "__call__"):
                daemon = Daemon(cast(Callable, server_behaviour))
            else:
                raise TypeError("Daemon must have trigger() or be of type Callable")
            self.subscribe_networking_daemon(sim, daemon, protocol, *ports)
            return server_behaviour

        return _decorator
