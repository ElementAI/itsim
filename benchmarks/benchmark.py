# Refs:
# https://www.blog.pythonlibrary.org/2016/05/24/python-101-an-intro-to-benchmarking-your-code/
# https://medium.freecodecamp.org/how-to-get-embarrassingly-fast-random-subset-sampling-with-python-da9b27d494d9

import time
from statistics import mean, variance

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

# ex: @benchmarker(100)
def benchmarker(iterations):
    def real_benchmarker(func):
        """
        A timer decorator
        """
        def function_timer(*args, **kwargs):
            """
            A nested function for timing other functions
            """
            results = []
            for i in range(iterations):
                start = time.time()
                value = func(*args, **kwargs)
                results.append(time.time() - start)

            stat = {"mean": mean(results),
                    "variance": variance(results),
                    "min": min(results),
                    "max": max(results)}

            return value, stat
        return function_timer
    return real_benchmarker


