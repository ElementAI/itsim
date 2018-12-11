from greensim.random import uniform, normal
from itsim.units import MS
from benchmarks.benchmark import benchmarker
import numpy as np

@benchmarker
def numpy_uniform(size):
    return np.random.uniform(low=100 * MS, high=200 * MS, size=size)

@benchmarker
def grsim_uniform(size):
    results=[]
    for i in range(size):
        results.append(next(uniform(100 * MS, 200 * MS)))
    return results

@benchmarker
def numpy_normal(size):
    return np.random.standard_normal(size=size)

@benchmarker
def grsim_normal(size):
    results=[]
    for i in range(size):
        results.append(next(normal(mean=0, std_dev=1)))
    return results


if __name__ == '__main__':

    sizes = [1, 10, 100, 1000, 10000]

    print("Comparing Numpy vs Greensim(Python's Random) for 'uniform' generator")
    for sz in sizes:
        print(f"\nBenchmarking size {sz}")
        np_values, np_avg = numpy_uniform(sz)
        gr_values, gr_avg = grsim_uniform(sz)
        print(f"Numpy speedup: {gr_avg/np_avg}\n")

    print("\nComparing Numpy vs Greensim(Python's Random) for 'standard normal' generator")
    for sz in sizes:
        print(f"\nBenchmarking size {sz}")
        np_values, np_avg = numpy_normal(sz)
        gr_values, gr_avg = grsim_normal(sz)
        print(f"Numpy speedup: {gr_avg/np_avg}\n")


