from numbers import Real
from typing import cast, TypeVar, Optional

from greensim.random import VarRandom, linear, bounded, project_int


T = TypeVar("T")


def num_bytes(gen: VarRandom[Real], header: Real = cast(Real, 0.0), upper: Optional[Real] = None) -> VarRandom[int]:
    yield from project_int(bounded(linear(gen, 1.0, header), 0.0, upper))
