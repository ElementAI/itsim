from itsim.machine.node import Node


class Endpoint(Node):
    """
    General-purpose computer, on which we have complete behaviour visibility through agent telemetry.
    """

    def __init__(self) -> None:
        raise NotImplementedError()
