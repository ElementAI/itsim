from typing import Callable

from greensim import labeled
from itsim.it_objects import ITTag

def malware() -> Callable:
    """
    Convenience decorator for identifying malware.
    Through the methods in greensim this label is cascaded through the actions of the Process
    """
    return labeled(ITTag.MALWARE)
