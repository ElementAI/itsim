from itsim.network import _Connection
from itsim.machine.process_management import _Service


class Connection(_Connection):
    """
    Connection object, tying a network interface of a node to a certain link.
    """

    def setup(self, *services: _Service):
        """
        Lists services that the node connected to the link should arrange and get running.
        """
        raise NotImplementedError()
