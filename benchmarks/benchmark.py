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
def benchmarker(iterations=1):
    def real_benchmarker(func):
        def function_timer(*args, **kwargs):
            results = []
            for i in range(iterations):
                start = time.time()
                value = func(*args, **kwargs)
                results.append(time.time() - start)

            stat = {"mean": mean(results),
                    "variance": [variance(results) if iterations >1 else -1.0],
                    "min": min(results),
                    "max": max(results)}

            return value, stat
        return function_timer
    return real_benchmarker


