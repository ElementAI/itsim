from itsim.units import MS
import numpy as np
from benchmarks.benchmark import benchmarker
import functools
from greensim.random import uniform, bounded

iterations = 100

class RandomGenerator():
    def __init__(self, type, *args, **kwargs):

        self._fn_map = {'uniform': functools.partial(np.random.uniform, *args, **kwargs),
                        'normal': functools.partial(np.random.standard_normal, *args, **kwargs),
                        'expo': functools.partial(np.random.exponential, *args, **kwargs)}
        assert type in self._fn_map
        self._fn = self._fn_map[type]
        self._queue_size = 100000
        self.fill_queue()

    def fill_queue(self):
        self._queue = [value for value in self._fn(size=self._queue_size).tolist()]

    def get(self):
        if len(self._queue) == 0:
            self.fill_queue()
        return self._queue.pop()

@benchmarker(iterations)
def benchmark_rg(sz):
    rg = RandomGenerator("uniform", low=100 * MS, high=200 * MS)
    return [rg.get() for _ in range(sz)]


@benchmarker(iterations)
def benchmark_greensim(gn, size):
    return [next(gn) for _ in range(size)]


temp_list = [data for data in range(100000)]
def get():
    return temp_list.pop()

@benchmarker(iterations)
def benchmark_get():
    return get()


if __name__ == '__main__':
    # sizes = [1,10,1000, 10000, 100000, 1000000]
    sizes = [1,100000]

    for sz in sizes:
        _, stats = benchmark_rg(sz)
        print(f'NUMPY QUEUE - Size{sz}: {stats}')

        _, stats = benchmark_greensim(bounded(uniform(100 * MS, 200 * MS), lower=0.0), sz)
        print(f'GREENSIM BOUNDED - Size{sz}: {stats}')

        _, stats = benchmark_greensim(uniform(100 * MS, 200 * MS), sz)
        print(f'GREENSIM - Size{sz}: {stats}')

        _, stats = benchmark_get()
        print(f'SINGLE GET: {stats}')

'''
    Conclusions: 
        - Cost per random value: 0.30 - 0.37us (depending on how benchmarking is done)
        - Simple get() benchmark: 0.27us
        
        - Greensim bounded: 0.57us
        - Greensim (unbounded): 0.36us
        
        - First benchmark (comparative_benchmark.py) was a bit misleading: iterating and returning an entire array at once is faster than 
          accessing values one at a time. 
                
        Size1,          Queue size 1000: {'mean': 5.192041397094727e-05, 'variance': [9.995927264368e-11], 'min': 4.792213439941406e-05, 'max': 0.00011396408081054688}
        Size10,         Queue size 1000: {'mean': 5.231618881225586e-05, 'variance': [1.4827812513183084e-11], 'min': 5.078315734863281e-05, 'max': 8.7738037109375e-05}
        Size1000,       Queue size 1000: {'mean': 0.0003675436973571777, 'variance': [9.965410329485424e-10], 'min': 0.000354766845703125, 'max': 0.00061798095703125}
        Size10000,      Queue size 1000: {'mean': 0.0036916232109069826, 'variance': [2.6420674436224662e-08], 'min': 0.0035479068756103516, 'max': 0.004529237747192383}
        Size100000,     Queue size 1000: {'mean': 0.0374685788154602, 'variance': [2.8304087166561383e-06], 'min': 0.0355527400970459, 'max': 0.04274892807006836}
        Size1000000,    Queue size 1000: {'mean': 0.36826502323150634, 'variance': [3.252774375401126e-05], 'min': 0.3598823547363281, 'max': 0.39007067680358887}
'''
