# Refs:
# https://www.blog.pythonlibrary.org/2016/05/24/python-101-an-intro-to-benchmarking-your-code/
# https://medium.freecodecamp.org/how-to-get-embarrassingly-fast-random-subset-sampling-with-python-da9b27d494d9

import time

class ContextTimer():
    def __init__(self, fct):
        self._fct = fct
        self._start = time.time()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        end = time.time()
        self._runtime = end - self._start
        print(f'The function {self._fct} took:\n{self._runtime} s')

# @benchmarker
def benchmarker(func):
    """
    A timer decorator
    """
    def function_timer(*args, **kwargs):
        """
        A nested function for timing other functions
        """
        nb_iterations = 100
        results = []
        time_avg = 0

        for i in range(nb_iterations):
            start = time.time()
            value = func(*args, **kwargs)
            end = time.time()
            runtime = end - start

            time_avg = runtime + time_avg
            results.append((time_avg, value))

        time_avg = time_avg/nb_iterations
        runtime_msg = f"{func.__name__}\t avg:{time_avg} s"
        print(runtime_msg)
        return value, time_avg
    return function_timer



