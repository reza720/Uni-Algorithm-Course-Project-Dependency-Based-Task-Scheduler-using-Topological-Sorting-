# Dependency-Based Task Scheduler (Topological Sort)

Final project for Algorithms, Section 001, Fall 2026, American University of
Afghanistan. Instructor: Dr. Umut Tosun.

The program reads a list of tasks and "X must be done before Y" rules, builds
a directed graph, and prints a valid order using Kahn's algorithm. If the rules
contain a cycle, it prints the required error message and shows one cycle so
the user can see which rule to fix.

## Team

| Member | AUAF ID | Role |
|---|---|---|
| Raufa Rauf | 49277 | Graph Architect (graph structure, input parser) |
| Sweeta Latifi | 45884 | Algorithm Developer (Kahn's algorithm, GUI) |
| Reza Panahi | 49780 | Cycle Checker & Tester (cycle report, tests, demo) |
| Ehsanullah Naseri | 49783 | Interface & I/O Lead (CLI, revisions, report) |

## Requirements

Python 3.8 or newer. Nothing to install: only the standard library is used
(Tkinter for the GUI ships with Python on Windows and macOS; on Ubuntu run
`sudo apt install python3-tk` if it is missing).

## How to run

Open a terminal in this folder (`topo_sort`).

GUI:

    python task_scheduler_gui.py

Type the tasks and dependencies or press **Load File...** and choose a file
from `samples`. **Find Order** (or Ctrl+Enter) runs the scheduler.

Command line:

    python task_scheduler.py samples/input1_valid.txt
    python task_scheduler.py samples/input2_cycle.txt -o result.txt
    python task_scheduler.py          # interactive: type tasks, then rules

Exit code is 0 for a valid order, 1 for a cycle and 2 for an input error.

Tests:

    python -m unittest discover -s tests -v

## Input format

    Tasks: A, B, C, D
    Dependencies:
    A -> B
    B -> C
    C -> D

`A -> B` means A must be finished before B. Text after `#` is a comment.
The `Tasks:` line is optional; any task named in a rule is added
automatically.

## Files

| File | Purpose |
|---|---|
| `task_scheduler.py` | Graph, parser, Kahn's algorithm, cycle finder, command line |
| `task_scheduler_gui.py` | Tkinter interface that draws the graph |
| `tests/test_task_scheduler.py` | 27 automated test cases |
| `samples/inputN_*.txt` | Sample inputs (valid, cycle, courses, self-loop, release plan, bad format) |
| `samples/outputN.txt` | Expected output for each sample |
| `screenshots/` | GUI screenshots used in the report and presentation |
| `Project_Report.pdf` / `.docx` | Project report |
