from fuzzingbook import GreyboxFuzzer as gbf
from fuzzingbook import Coverage as cv
from fuzzingbook import MutationFuzzer as mf

import traceback
import numpy as np
import time
import random

from bug import entrypoint
from bug import get_initial_corpus

import signal
from typing import Union, Any, Type, Optional
from types import FrameType, TracebackType
## You can re-implement the coverage class to change how
## the fuzzer tracks new behavior in the SUT

# class MyCoverage(cv.Coverage):
#
#     def coverage(self):
#         <your implementation here>
#
#     etc...


## You can re-implement the runner class to change how
## the fuzzer tracks new behavior in the SUT

# class MyRunner(mf.FunctionRunner):
#
#     def run_function(self, inp):
#           <your implementation here>
#
#     def coverage(self):
#           <your implementation here>
#
#     etc...


## You can re-implement the fuzzer class to change your
## fuzzer's overall structure

# class MyFuzzer(gbf.GreyboxFuzzer):
#
#     def reset(self):
#           <your implementation here>
#
#     def run(self, runner: gbf.FunctionCoverageRunner):
#           <your implementation here>
#   etc...

## The Mutator and Schedule classes can also be extended or
## replaced by you to create your own fuzzer!


class SignalTimeout:
    """Execute a code block raising a timeout."""

    def __init__(self, timeout: Union[int, float]) -> None:
        """
        Constructor. Interrupt execution after `timeout` seconds.
        """
        self.timeout = timeout
        self.old_handler: Any = signal.SIG_DFL
        self.old_timeout = 0.0

    def __enter__(self) -> Any:
        """Begin of `with` block"""
        # Register timeout() as handler for signal 'SIGALRM'"
        self.old_handler = signal.signal(signal.SIGALRM, self.timeout_handler)
        self.old_timeout, _ = signal.setitimer(signal.ITIMER_REAL, self.timeout)
        return self

    def __exit__(self, exc_type: Type, exc_value: BaseException,
                 tb: TracebackType) -> None:
        """End of `with` block"""
        self.cancel()
        return  # re-raise exception, if any

    def cancel(self) -> None:
        """Cancel timeout"""
        signal.signal(signal.SIGALRM, self.old_handler)
        signal.setitimer(signal.ITIMER_REAL, self.old_timeout)

    def timeout_handler(self, signum: int, frame: Optional[FrameType]) -> None:
        """Handle timeout (SIGALRM) signal"""
        raise TimeoutError()
# When executed, this program should run your fuzzer for a very 
# large number of iterations. The benchmarking framework will cut 
# off the run after a maximum amount of time
#
# The `get_initial_corpus` and `entrypoint` functions will be provided
# by the benchmarking framework in a file called `bug.py` for each 
# benchmarking run. The framework will track whether or not the bug was
# found by your fuzzer -- no need to keep track of crashing inputs
def get_results():
    print("enters base")
    base_results = []
    events = []
    for i in range(5):
        start = time.time()
        try:
            # reset seed for each run
            random.seed()
            with SignalTimeout(300.0):
                seed_inputs = get_initial_corpus()
                fast_schedule = gbf.AFLFastSchedule(5)
                line_runner = mf.FunctionCoverageRunner(entrypoint)

                fast_fuzzer = gbf.CountingGreyboxFuzzer(seed_inputs, gbf.Mutator(), fast_schedule)
                fast_fuzzer.runs(line_runner, trials=999999999)
        except TimeoutError:
            #print("timeout, ", end - start)
            base_results.append(300)
            events.append(1)
            print("timeout")
        except:
            end = time.time()
            #print("success, ", end - start)
            base_results.append(end - start)
            events.append(0)
    #base_results = numpy.array(base_results)
    return base_results, events
    #print()
    #print("Baseline mean: ", base_results.mean())
    #print("Baseline std: ", base_results.std(ddof=1))