from greensim.random import normal, constant

from itsim.machine.node import Socket
from itsim.machine.process_management import _Thread
from itsim.network.link import Link
from itsim.network.location import Location
from itsim.network.packet import Packet, Payload, PayloadDictionaryType
from itsim.network.router import Router
from itsim.network.service.dhcp import DHCPDaemon
from itsim.simulator import Simulator
from itsim.types import as_port, Protocol

from pytest import raises

from unittest.mock import MagicMock, patch


router = Router()


def pack_send():
    global router
    bound_sock = router._sockets[as_port(67)]

    for req, res in DHCPDaemon.responses.items():
        bound_sock._enqueue(
            Packet(
                Location(),
                Location(),
                0,
                Payload({PayloadDictionaryType.CONTENT: req})))


class AdHocError(Exception):
    pass


# Since send behavior is not defined as of this moment, this mocks it out and checks that it runs
class MockDHCP(DHCPDaemon):
    def __init__(self):
        pass

    def _trigger_event(self, thread: _Thread, packet: Packet, socket: Socket) -> None:
        type_msg = packet.payload.entries[PayloadDictionaryType.CONTENT]
        assert type_msg in self.responses

        socket.send = MagicMock()
        super()._trigger_event(thread, packet, socket)

        # This is of the form (args, kwargs) = socket.send.call_args
        ((source, size, pay), _) = socket.send.call_args
        expected_pay = Payload({PayloadDictionaryType.CONTENT: self.responses[type_msg]})
        assert packet.source == source
        # This value is random
        assert int == type(size)
        assert expected_pay == pay
        raise AdHocError()


@patch("itsim.network.link.Link")
def test_integ(wan):
    global router
    sim = Simulator()
    sim.add_in(1, pack_send)

    link = Link("10.1.128.0/18", normal(0, 1), constant(1))
    router = router.with_daemon_on(sim, link, MockDHCP(), Protocol.UDP, 67)

    with raises(AdHocError):
        sim.run()
