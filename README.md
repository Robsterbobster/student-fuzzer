# Student Fuzzer
Template repository for CS5219

## Setup
Install all dependencies needed by the Fuzzing Book baseline fuzzer with:

```
pip install -r requirements.txt
```

You may want to do this in a Python **virtual environment** to avoid global dependency conflicts.

## Usage

The fuzzer expects a file named `bug.py` to be *in the same directory as the fuzzer file* (`student-fuzzer.py`).
This `bug.py` file should have two functions: an `entrypoint` that is fuzzed by the fuzzer and `get_initial_corpus` function which returns a list of initial inputs for the fuzzer.
To execute the fuzzer on the bug in `bug.py`, just run:

```
python student_fuzzer.py
```

Several example bugs are included in the `examples` directory.
To run the fuzzer on an example bug, copy e.g. `examples/0/bug.py` to the base directory of this repository before running the fuzzer with the command above.

To run the test that compares baseline fuzzer and improved fuzzer, run:
```
python test.py
```
## Layout
The project is organized as follows:

- `base_student_fuzzer.py`: The baseline fuzzer used for testing
- `bug.py`: The input buggy program
- `Example.py`: The example buggy program in the report
- `student_fuzzer.py`: The improved fuzzer
- `plot.png`: The bar plot that shows the time taken for baseline and improved fuzzer on the example bug, along with the standard deviation
- `test.py`: The automatic test that compares baseline and improved fuzzer on the `bug.py` file
- `experiment_output.txt`: The output that is manually copied from the terminal when executing `test.py` file
- Other files such as `Dockerfile` already exists in the directory and not related to the improved fuzzer