from itsim.simulator import Simulator
from itsim.node import Node


class Endpoint(Node):
    """
    General-purpose computer, on which we have complete behaviour visibility through agent telemetry.

    :param sim: Simulator instance to which this endpoint participates.
    """

    def __init__(self, sim: Simulator) -> None:
        raise NotImplementedError()
