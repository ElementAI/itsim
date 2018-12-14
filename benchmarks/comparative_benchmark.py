from greensim.random import uniform, normal, bounded, expo
from itsim.units import MS
from benchmarks.benchmark import benchmarker
import numpy as np
import random
from texttable import Texttable
import functools
from multiprocessing import Process, Queue

iterations=1


'''
    !!!
    Warning: those tests are biased; they don't perform exactly the same operations for accessing the generated 
    numbers. This has been proven to make a huge different in subsequent testing (random_generator_benchmark.py)
    !!!
'''


def queue_creator(q, fn, *args, **kwargs):
    data = fn(*args, **kwargs).tolist()
    q.put(-1) # to waste on sync
    [q.put(data_entry) for data_entry in data]
    q.put(-1)
    print("Put done")

@benchmarker(iterations)
def measure_greensim(gn, size=1):
    return [next(gn) for _ in range(size)]


@benchmarker(iterations)
def measure_numpy(fn, *args, **kwargs):
    return fn(*args, **kwargs)

@benchmarker(iterations)
def measure_numpy_process(q=None, size=1):
    return [q.get() for _ in range(size)]
    # return q.get()

@benchmarker(iterations)
def measure_random(fn, *args, **kwargs):
    size = kwargs.pop('size')
    return [fn(*args, **kwargs) for _ in range(size)]


def print_benchmark_info(benchmark_stats):

    fct_names = []
    implementations = []
    for fct_stats in benchmark_stats:
        for fct_stat in fct_stats:
            for key, value in fct_stat.items():
                if key == "function" and value not in fct_names:
                    fct_names.append(value)
                elif isinstance(value, dict) and key not in implementations:
                    implementations.append(key)

    t_summary = Texttable()
    t_summary_rows = []
    t_summary_header = ['Function', 'Size']
    [t_summary_header.append(f"{implementations[0]}/{impl}") for impl in implementations]
    t_summary_rows.append(t_summary_header)

    ttables = [(impl, Texttable(), list()) for impl in implementations]
    detailed_results_header = ['Function', 'Size', 'Min', 'Max', 'Variance', 'Mean']

    [ttable[2].append(detailed_results_header) for ttable in ttables]

    for fct_stats in benchmark_stats:
        for stats_for_size in fct_stats:
            for ttable in ttables:
                impl = ttable[0]
                ttable_rows = ttable[2]
                ttable_rows.append([stats_for_size["function"],
                                stats_for_size["size"],
                                stats_for_size[impl]["min"],
                                stats_for_size[impl]["max"],
                                stats_for_size[impl]["variance"],
                                stats_for_size[impl]["mean"]])

            summary_list = [stats_for_size["function"], stats_for_size["size"]]
            [summary_list.append(stats_for_size[implementations[0]]["mean"]/stats_for_size[impl]["mean"]) for impl in implementations]
            t_summary_rows.append(summary_list)

    print("\n")
    for ttable in ttables:
        table_name = ttable[0]
        table = ttable[1]
        table_rows = ttable[2]
        print(f"\n{table_name} ({iterations} iterations)")
        table.set_cols_width([10, 10, 25,25,25,25])
        table.set_cols_dtype(["t", "t","t", "t","t", "t"])
        table.add_rows(table_rows)
        print(table.draw())

    print(f"\nSUMMARY: Speedup over {implementations[0]}")
    t_summary.add_rows(t_summary_rows)
    print(t_summary.draw())


def numpy_process_setup(sz):
    # Numpy process setup
    q = Queue()
    fn = functools.partial(np.random.uniform, low = 100 * MS, high = 200 * MS)
    process_one = Process(target=queue_creator, args=(q, fn), kwargs={'size':sz})
    process_one.start()
    q.get(True, 1)
    return q, process_one


def numpy_process_teardown(q, process_one):
    #Numpy process teardown
    q.close()
    q.join_thread()
    process_one.join()


def run_benchmark_definition(benchmark_definition, sizes):
    benchmark_stats = []
    for fct in benchmark_definition:
        print(f"\nBenchmarking {fct['name']}", end='')
        fct_stats=[]
        for sz in sizes:
            print(".", end='')
            sz_stat = {}
            sz_stat["function"]=fct['name']
            sz_stat["size"]=sz
            for test in fct['test_list']:
                test_name = test[0]
                partial_fct = test[1]
                setup_cfg = {}
                if test_name == 'numpy_process':
                    q, process_one = numpy_process_setup(sz)
                    _, sz_stat[test_name] = partial_fct(q=q, size=sz)
                    numpy_process_teardown(q, process_one)
                else:
                    _, sz_stat[test_name] = partial_fct(size=sz)
            fct_stats.append(sz_stat)
        benchmark_stats.append(fct_stats)
    return benchmark_stats

if __name__ == '__main__':
    benchmark_definition_0 = [{"name": "Uniform",
                             "test_list":[("random", functools.partial(measure_random, random.uniform, 0, 1)),
                                          ("numpy", functools.partial(measure_numpy, np.random.uniform, low=100 * MS, high=200 * MS)),
                                          ("numpy_process", functools.partial(measure_numpy_process)),
                                          ("greensim", functools.partial(measure_greensim, uniform(100 * MS, 200 * MS))),
                                          ("greensim_bounded", functools.partial(measure_greensim, bounded(uniform(100 * MS, 200 * MS), lower=0.0)))]
                            }]
    sizes = [1, 10, 100, 100000]
    benchmark_stats = run_benchmark_definition(benchmark_definition_0, sizes)
    print_benchmark_info(benchmark_stats)

    benchmark_definition_1 = [{"name": "Uniform",
                             "test_list":[("random", functools.partial(measure_random, random.uniform, 0, 1)),
                                          ("numpy", functools.partial(measure_numpy, np.random.uniform, low=100 * MS, high=200 * MS)),
                                          ("greensim", functools.partial(measure_greensim, uniform(100 * MS, 200 * MS))),
                                          ("greensim_bounded", functools.partial(measure_greensim, bounded(uniform(100 * MS, 200 * MS), lower=0.0)))]
                            },
                            {"name": "Normal",
                             "test_list":[("random", functools.partial(measure_random, random.normalvariate, 0, 1)),
                                          ("numpy", functools.partial(measure_numpy, np.random.standard_normal)),
                                          ("greensim", functools.partial(measure_greensim, uniform(100 * MS, 200 * MS))),
                                          ("greensim", functools.partial(measure_greensim, uniform(100 * MS, 200 * MS))),
                                          ("greensim_bounded", functools.partial(measure_greensim, bounded(normal(mean=0, std_dev=1), lower=0.0)))]
                             },
                            {"name": "Expo",
                             "test_list":[("random", functools.partial(measure_random, random.expovariate, 1)),
                                          ("numpy", functools.partial(measure_numpy, np.random.exponential)),
                                          ("greensim", functools.partial(measure_greensim, expo(1.0))),
                                          ("greensim", functools.partial(measure_greensim, expo(1.0))),
                                          ("greensim_bounded", functools.partial(measure_greensim, bounded(expo(mean=1.0), lower=0.0)))]
                             }]
    sizes = [1, 10, 100, 100000]
    benchmark_stats = run_benchmark_definition(benchmark_definition_1, sizes)
    print_benchmark_info(benchmark_stats)
