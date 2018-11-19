from itsim.network.packet import Packet, Payload, PayloadDictionaryType
from itsim.network.service.dhcp import DHCPDaemon
from itsim.types import as_address

from unittest.mock import patch


def test_empty_init():
    DHCPDaemon()


def apply_trigger(thread, socket, req, res):
    packet = Packet(as_address(None),
                    as_address(None),
                    0,
                    Payload({PayloadDictionaryType.CONTENT: req}))
    print(packet.payload)
    DHCPDaemon()._trigger_event(thread, packet, socket)
    # This is of the form (args, kwargs) = socket.send.call_args
    ((source, size, pay), _) = socket.send.call_args
    expected_pay = Payload({PayloadDictionaryType.CONTENT: res})
    assert packet.source == source
    # This value is random
    assert int == type(size)
    assert expected_pay == pay


@patch("itsim.machine.process_management.thread.Thread")
@patch("itsim.machine.node.Socket")
def test_trigger_inputs(thread, socket):
    apply_trigger(thread, socket, "DHCPDISCOVER", "DHCPOFFER")
    apply_trigger(thread, socket, "DHCPREQUEST", "DHCPACK")
