from itsim.machine.process_management.daemon import Daemon
from itsim.network.router import Router
from itsim.types import Protocol

from unittest.mock import MagicMock, patch


def test_init():
    Router()


@patch("itsim.simulator.Simulator")
@patch("itsim.network.link.Link")
def test_with_daemon_on(sim, link):
    router = Router()
    router.connected_to = MagicMock()

    ret = router.with_daemon_on(sim,
                                link,
                                Daemon(lambda: 0),
                                Protocol.UDP,
                                1)

    # These are the two effects which can be tested directly
    # The others involve simulation events and are handled in
    # tests/integ/test_dhcp_integ.py
    router.connected_to.assert_called_with(link)
    assert 1 in router._port_table
    assert router == ret
