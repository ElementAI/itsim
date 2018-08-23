from typing import Callable

from greensim import tagged
from itsim.it_objects import ITTag


def malware(event: Callable) -> Callable:
    """
    Convenience decorator for identifying malware.
    Through the methods in greensim this label is cascaded through the actions of the Process
    """
    return tagged(ITTag.MALWARE)(event)
