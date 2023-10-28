import ast
import random
from typing import Any, Set, Tuple, Sequence, Dict, List

from fuzzingbook import GreyboxFuzzer as gbf
from fuzzingbook import Coverage as cv
from fuzzingbook import MutationFuzzer as mf

import traceback
import numpy as np
import time

from bug import entrypoint
from bug import get_initial_corpus

## You can re-implement the coverage class to change how
## the fuzzer tracks new behavior in the SUT
NAME = 'entrypoint'
n_gram = 4
#n_gram_type = Tuple[cv.Location, cv.Location, cv.Location, cv.Location, cv.Location]
n_gram_type = cv.Location
Hashmap = Dict[int, int]
class MyCoverage(cv.Coverage):
    def coverage(self) -> Set[n_gram_type]:
        """The set of executed lines, as (function_name, line_number) pairs"""
        """
        trace = self.trace()
        branches = set()
        for i in range(len(trace)-(n_gram+1)):
            branches.add(tuple(trace[i:i+(n_gram+1)]))
        return branches
        """
        return set(self.trace())

    """
        def getPathID(self, branch: Set[n_gram_type]) -> str:
        ls = list(branch)
        for i in range(len(ls)):
    """



## You can re-implement the runner class to change how
## the fuzzer tracks new behavior in the SUT
class MyRunner(mf.FunctionRunner):
    def run_function(self, inp: str) -> Any:
        with MyCoverage() as cov:
            try:
                result = super().run_function(inp)
            except Exception as exc:
                self._coverage = cov.coverage()
                raise exc

        self._coverage = cov.coverage()
        return result

    def coverage(self) -> Set[n_gram_type]:
        return self._coverage

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

class MyMutator(gbf.Mutator):
    def mutate(self, inp: Any) -> Any:  # can be str or Seed (see below)
        """Return s with a random mutation applied. Can be overloaded in subclasses."""
        mutator = random.choice(self.mutators)
        i = mutator(inp)
        print((i))
        return i
class MyFuzzer(gbf.GreyboxFuzzer):
    """Count how often individual paths are exercised."""
    def reset(self):
        """Reset path frequency"""
        super().reset()
        self.schedule.path_frequency = {}

    def run(self, runner: MyRunner) -> Tuple[Any, str]:  # type: ignore
        """Inform scheduler about path frequency"""
        result, outcome = super().run(runner)

        path_id = gbf.getPathID(runner.coverage())
        if path_id not in self.schedule.path_frequency:
            self.schedule.path_frequency[path_id] = 1
        else:
            self.schedule.path_frequency[path_id] += 1

        return(result, outcome)


class MySchedule(gbf.PowerSchedule):
    """Exponential power schedule as implemented in AFL"""

    def __init__(self, exponent: float) -> None:
        self.exponent = exponent

    def assignEnergy(self, population: Sequence[gbf.Seed]) -> None:
        """Assign exponential energy inversely proportional to path frequency"""
        for seed in population:
            seed.energy = 1 / (self.path_frequency[gbf.getPathID(seed.coverage)] ** self.exponent)

class FunctionFinder(ast.NodeVisitor):
    def __init__(self):
        self.function_name = NAME
        self.function_node = None

    def visit_FunctionDef(self, node):
        if node.name == self.function_name:
            self.function_node = node

class LafIntelTransformer(ast.NodeTransformer):
    def visit_If(self, node):
        # if integer comparison

        return node
# When executed, this program should run your fuzzer for a very 
# large number of iterations. The benchmarking framework will cut 
# off the run after a maximum amount of time
#
# The `get_initial_corpus` and `entrypoint` functions will be provided
# by the benchmarking framework in a file called `bug.py` for each 
# benchmarking run. The framework will track whether or not the bug was
# found by your fuzzer -- no need to keep track of crashing inputs
if __name__ == "__main__":
    for i in range(10):
        start = time.time()
        try:
            seed_inputs = get_initial_corpus()
            fast_schedule = MySchedule(5)
            line_runner = MyRunner(entrypoint)

            fast_fuzzer = MyFuzzer(seed_inputs, MyMutator(), fast_schedule)
            fast_fuzzer.runs(line_runner, trials=999999999)
        except:
            end = time.time()
            print(end-start)
