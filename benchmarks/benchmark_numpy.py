from greensim.random import uniform, normal, bounded, expo
from itsim.units import MS
from benchmarks.benchmark import benchmarker
import numpy as np
import random
from texttable import Texttable

iterations=50

@benchmarker(iterations)
def measure_greensim(size, gn):
    return [next(gn) for _ in range(size)]

@benchmarker(iterations)
def measure_numpy(fn, *args, **kwargs):
    return fn(*args, **kwargs)


@benchmarker(iterations)
def measure_random(size, fn, *args, **kwargs):
    return [fn(*args, **kwargs) for _ in range(size)]


def benchmark_uniform(sizes):
    print("\nRunning Uniform Generator", end='')
    uniform_gen = bounded(uniform(100 * MS, 200 * MS), lower=0.0)
    stats=[]
    for sz in sizes:
        print(".", end='')
        stat = {}
        stat["function"]="uniform"
        stat["size"]=sz
        _, stat["numpy"] = measure_numpy(np.random.uniform, low=100 * MS, high=200 * MS, size=sz)
        _, stat["random"] = measure_random(sz, random.uniform, 0, 1)
        _, stat["greensim"] = measure_greensim(sz, uniform(100 * MS, 200 * MS))
        _, stat["greensim_bounded"] = measure_greensim(sz, uniform_gen)
        stats.append(stat)
    return stats, "Uniform"

def benchmark_normal(sizes):
    print("\nRunning Normal Generator", end='')
    normal_gen = bounded(normal(mean=0, std_dev=1), lower=0.0)
    stats=[]
    for sz in sizes:
        print(".", end='')
        stat = {}
        stat["function"]="normal"
        stat["size"]=sz
        _, stat["numpy"] = measure_numpy(np.random.standard_normal, size=sz)
        _, stat["random"] = measure_random(sz, random.normalvariate, 0, 1)
        _, stat["greensim"] = measure_greensim(sz, uniform(100 * MS, 200 * MS))
        _, stat["greensim_bounded"] = measure_greensim(sz, normal_gen)
        stats.append(stat)
    return stats, "Normal"

def benchmark_expo(sizes):
    print("\nRunning Expo Generator", end='')
    expo_gen = bounded(expo(mean=1.0), lower=0.0)
    stats=[]
    for sz in sizes:
        print(".", end='')
        stat = {}
        stat["function"]="expo"
        stat["size"]=sz
        _, stat["numpy"] =  measure_numpy(np.random.exponential, size=sz)
        _, stat["random"] = measure_random(sz, random.expovariate, 1)
        _, stat["greensim"] = measure_greensim(sz, expo(1.0))
        _, stat["greensim_bounded"] = measure_greensim(sz, expo_gen)
        stats.append(stat)
    return stats, "Expo"

def print_benchmark_info(benchmark_stats):

    t_numpy = Texttable()
    t_random = Texttable()
    t_greensim = Texttable()
    t_greensim_bounded = Texttable()

    t_summary_ratio = Texttable()
    t_summary_ratio_rows = []
    t_summary_ratio_rows.append(['Function', 'Size', 'Random', 'Random/Numpy', 'Random/Greensim', 'Random/Greensim_bounded'])

    detailed_results_header = ['Function', 'Size', 'Min', 'Max', 'Variance', 'Mean']
    t_numpy_rows = []
    t_numpy_rows.append(detailed_results_header)

    t_random_rows = []
    t_random_rows.append(detailed_results_header)

    t_greensim_rows = []
    t_greensim_rows.append(detailed_results_header)

    t_greensim_bounded_rows = []
    t_greensim_bounded_rows.append(detailed_results_header)

    for fct_data in benchmark_stats:
        fct_stats = fct_data[0]

        for stats_for_size in fct_stats:
            t_numpy_rows.append([stats_for_size["function"],
                            stats_for_size["size"],
                            stats_for_size["numpy"]["min"],
                            stats_for_size["numpy"]["max"],
                            stats_for_size["numpy"]["variance"],
                            stats_for_size["numpy"]["mean"]])

            t_random_rows.append([stats_for_size["function"],
                                 stats_for_size["size"],
                                 stats_for_size["random"]["min"],
                                 stats_for_size["random"]["max"],
                                 stats_for_size["random"]["variance"],
                                 stats_for_size["random"]["mean"]])

            t_greensim_rows.append([stats_for_size["function"],
                                 stats_for_size["size"],
                                 stats_for_size["greensim"]["min"],
                                 stats_for_size["greensim"]["max"],
                                 stats_for_size["greensim"]["variance"],
                                 stats_for_size["greensim"]["mean"]])

            t_greensim_bounded_rows.append([stats_for_size["function"],
                                 stats_for_size["size"],
                                 stats_for_size["greensim_bounded"]["min"],
                                 stats_for_size["greensim_bounded"]["max"],
                                 stats_for_size["greensim_bounded"]["variance"],
                                 stats_for_size["greensim_bounded"]["mean"]])

            t_summary_ratio_rows.append([stats_for_size["function"],
                                         stats_for_size["size"],
                                         stats_for_size["random"]["mean"]/stats_for_size["random"]["mean"],
                                         stats_for_size["random"]["mean"]/stats_for_size["numpy"]["mean"],
                                         stats_for_size["random"]["mean"]/stats_for_size["greensim"]["mean"],
                                         stats_for_size["random"]["mean"]/stats_for_size["greensim_bounded"]["mean"]])

    print(f"\n\nRandom ({iterations} iterations)")
    t_random.set_cols_width([10, 10, 25,25,25,25])
    t_random.set_cols_dtype(["t", "t","t", "t","t", "t"])
    t_random.add_rows(t_random_rows)
    print(t_random.draw())

    print(f"\nNumpy ({iterations} iterations)")
    t_numpy.set_cols_width([10, 10, 25,25,25,25])
    t_numpy.set_cols_dtype(["t", "t","t", "t","t", "t"])
    t_numpy.add_rows(t_numpy_rows)
    print(t_numpy.draw())

    print(f"\nGreensim ({iterations} iterations)")
    t_greensim.set_cols_width([10, 10, 25,25,25,25])
    t_greensim.set_cols_dtype(["t", "t","t", "t","t", "t"])
    t_greensim.add_rows(t_greensim_rows)
    print(t_greensim.draw())

    print(f"\nGreensim_bounded ({iterations} iterations)")
    t_greensim_bounded.set_cols_width([10, 10, 25,25,25,25])
    t_greensim_bounded.set_cols_dtype(["t", "t", "t", "t", "t", "t"])
    t_greensim_bounded.add_rows(t_greensim_bounded_rows)
    print(t_greensim_bounded.draw())

    print("\nSUMMARY: Speedup over Random")
    t_summary_ratio.add_rows(t_summary_ratio_rows)
    print(t_summary_ratio.draw())


# Function  Size    Numpy   Random  Greensim    Greensim_bounded
if __name__ == '__main__':

    sizes = [1, 10, 100, 1000, 10000]
    functions = [benchmark_uniform, benchmark_normal, benchmark_expo]

    benchmark_stats = []
    [benchmark_stats.append(fn(sizes)) for fn in functions]
    print_benchmark_info(benchmark_stats)
