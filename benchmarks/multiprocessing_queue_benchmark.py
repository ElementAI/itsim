from itsim.units import MS
from multiprocessing import Process, Queue
import numpy as np
from benchmarks.benchmark import benchmarker
import time
import functools

sentinel = -1


def creator(q, fn, *args, **kwargs):
    data = fn(*args, **kwargs).tolist()
    [q.put(data_entry) for data_entry in data]
    q.put(-1)


def run_process_benchmarks(sizes):
    @benchmarker(1)
    def dequeue(q):
        # data = [0]
        # while data[-1] != sentinel:
        #     data.append(q.get())
        # return data
        return q.get()

    for sz in sizes:
        start = time.time()

        q = Queue()
        process_one = Process(target=creator, args=(q, np.random.uniform), kwargs={'size':sz,'low':100 * MS, 'high':200 * MS})
        process_one.start()

        _, stats = dequeue(q)

        q.close()
        q.join_thread()
        process_one.join()
        stop = time.time()
        print(f'Dequeuing {sz} from process: ')
        print(stats)
        print(f'Time including setup/teardown: {stop-start}')


class RandomGenerator():

    def __init__(self, type, queue_size=1000):
        self._fn_map = {'uniform': functools.partial(np.random.uniform, low=100 * MS, high=200 * MS),
                        'normal': functools.partial(np.random.standard_normal),
                        'expo': functools.partial(np.random.exponential)}
        assert type in self._fn_map
        self._fn = self._fn_map
        self.fill_queue()
        self._sz = queue_size

    def fill_queue(self):
        self._queue = [value for value in self._fn(size=self._sz).tolist()]

    def get(self):
        if len(self._queue)==0:
            self.fill_queue()
        return self._queue.pop()


if __name__ == '__main__':
    sizes = [1,10,100,1000,100000]
    run_process_benchmarks(sizes)

'''
    Notes: 
        -   Accessing a single element (created in a separate process) takes roughly 3ms. This is approx. 10000x slower 
            than generating a random number. 
'''
