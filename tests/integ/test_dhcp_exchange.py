from typing import List
# from unittest.mock import MagicMock, patch

from greensim.random import uniform, constant

from itsim.machine.endpoint import Endpoint
from itsim.machine.process_management import _Thread
from itsim.network.link import Link
from itsim.network.location import Location
from itsim.network.packet import Packet
from itsim.network.router import Router
from itsim.network.service.dhcp import DHCPDaemon
from itsim.simulator import Simulator
from itsim.types import as_port, Protocol, AddressRepr
from itsim.units import S, MS, MbPS

from pytest import raises


# router = Router()


# def pack_send():
#     global router
#     bound_sock = router._sockets[as_port(67)]

#     for req, res in DHCPDaemon.responses.items():
#         bound_sock._enqueue(
#             Packet(
#                 Location(),
#                 Location(),
#                 0,
#                 {"content": req}))


# class AdHocError(Exception):
#     pass


# # Since send behavior is not defined as of this moment, this mocks it out and checks that it runs
# class MockDHCP(DHCPDaemon):
#     def __init__(self):
#         pass

#     def _trigger_event(self, thread: _Thread, packet: Packet, socket: Socket) -> None:
#         type_msg = packet.payload["content"]
#         assert type_msg in self.responses

#         socket.send = MagicMock()
#         super()._trigger_event(thread, packet, socket)

#         # This is of the form (args, kwargs) = socket.send.call_args
#         ((source, size, pay), _) = socket.send.call_args
#         expected_pay = {"content": self.responses[type_msg]}
#         assert packet.source == source
#         # This value is random
#         assert int == type(size)
#         assert expected_pay == pay
#         raise AdHocError()


def set_addresses(*ars: AddressRepr):
    return {as_address(ar) for ar in ars}


# @patch("itsim.network.link.Link")
def test_dhcp_exchange():
    sim = Simulator()
    link = Link("10.1.128.0/18", uniform(100 * MS, 200 * MS), constant(100 * MbPS))
    router = Router().connected_to(link, "10.1.128.1") \
                     .with_daemon_on(sim, link, DHCPDaemon(100), Protocol.UDP, 67, 68)
    # router = router.with_daemon_on(sim, link, MockDHCP(), Protocol.UDP, 67)
    endpoints = []

    def add_endpoint(delay: float):
        endpoint = Endpoint().connected_to(link, dhcp_with=sim)
        assert set(endpoint.addresses()) == set_addresses("127.0.0.1", "10.1.128.0")
        endpoints.append(endpoint)

    for delay in [1.0, 2.0]:
        sim.add(add_endpoint, delay * S)
    sim.run(5.0 * S)

    for n, endpoint in enumerate(endpoints):
        assert set(endpoint.addresses()) == set_addresses("127.0.0.1", as_address(n + 100, link.cidr))
