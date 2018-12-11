from greensim.random import uniform, constant
from itsim.units import MS, MbPS
from benchmarks.benchmark import ContextTimer
import timeit
import cProfile

from tests.integ.test_broadcast import test_broadcast

if __name__ == '__main__':
    print("cProfile on test_broadcast()")
    cProfile.run('test_broadcast()')

    # Approx. 38 times generating latency and bandwidth random values in test_broadcast
    with ContextTimer("test_broadcast_random_values"):
        for i in range(38):
            next(uniform(100 * MS, 200 * MS))
            next(constant(100 * MbPS))

    print("Benchmarking test_broadcast()")
    setup = "from tests.integ.test_broadcast import test_broadcast"
    iters=10
    time_avg = timeit.timeit('test_broadcast()', setup=setup, number=iters)/iters
    print(f"Total simulation time: {time_avg} s")
