from numbers import Real
from typing import cast, TypeVar, Optional

from greensim.random import VarRandom, RandomOpt, linear, bounded, project_int


T = TypeVar("T")

VarRandomTime = VarRandom[float]
VarRandomSize = VarRandom[int]
VarRandomBandwidth = VarRandom[int]


def num_bytes(
    gen: VarRandom[Real],
    header: int = 0,
    upper: Optional[Real] = None,
    rng: RandomOpt = None
) -> VarRandom[int]:
    yield from project_int(bounded(linear(gen, 1.0, header), 0.0, upper))
