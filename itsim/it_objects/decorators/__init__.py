from typing import Callable

from greensim import tagged
from itsim.it_objects import Tag


def malware(event: Callable) -> Callable:
    """
    Convenience decorator for identifying malware.
    Through the methods in greensim this label is cascaded through the actions of the Process
    """
    return tagged(Tag.MALWARE)(event)
