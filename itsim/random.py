from numbers import Real
from typing import TypeVar, Optional

from greensim.random import VarRandom, RandomOpt, linear, bounded, project_int


T = TypeVar("T")

VarRandomTime = VarRandom[float]
VarRandomSize = VarRandom[int]
VarRandomBandwidth = VarRandom[float]


def num_bytes(
    gen: VarRandom[Real],
    header: int = 0,
    upper: Optional[Real] = None,
    rng: RandomOpt = None
) -> VarRandom[int]:
    """
    Random generator for buffers described only as a number of bytes to store or transfer.

    :param gen: Main model for the number of bytes in the buffer, as a number generator this one wraps around.
    :param header: Fixed number of bytes systematically added to the randomly generated number, acting as a fixed header
        to the buffer.
    :param upper: Maximum number of bytes to the buffer -- any number generated above this limited is clipped back.
    :param rng: Pseudo-random source (rarely set here).
    """
    yield from project_int(bounded(linear(gen, 1.0, header), 0.0, upper))
