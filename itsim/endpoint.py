from itsim.node import Node
from itsim.simulator import Simulator


class Endpoint(Node):
    """
    General-purpose computer, on which we have complete behaviour visibility through agent telemetry.
    """

    def __init__(self, sim: Simulator) -> None:
        """
        - :param sim: Simulator instance to which this endpoint participates.
        """
        raise NotImplementedError()
