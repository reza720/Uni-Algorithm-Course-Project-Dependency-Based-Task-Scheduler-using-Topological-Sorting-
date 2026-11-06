#!/usr/bin/env python3
"""
task_scheduler.py - Dependency-based task scheduler (topological sort).

Algorithms, Fall 2026, Section 001 - Final Project
American University of Afghanistan (AUAF), Instructor: Dr. Umut Tosun

Team
  Raufa Rauf         (49277)  Graph Architect: TaskGraph class, input parser
  Sweeta Latifi      (45884)  Algorithm Developer: Kahn's algorithm, GUI
  Reza Panahi        (49780)  Cycle Checker & Tester: cycle report, tests, demo
  Ehsanullah Naseri  (49783)  Interface & I/O Lead: CLI, revisions, report

Input format (file or interactive)
  Tasks: A, B, C, D          # optional list of task names
  Dependencies:              # optional section header
  A -> B                     # A must be finished before B
  B -> C
  Everything after '#' on a line is a comment. Blank lines are skipped.
  A task that appears only in a dependency line is added automatically.

Usage
  python task_scheduler.py samples/input1_valid.txt
  python task_scheduler.py samples/input2_cycle.txt -o result.txt
  python task_scheduler.py                (interactive mode)

Exit codes: 0 = valid order, 1 = cycle detected, 2 = input error.
"""

import argparse
import sys
from collections import defaultdict, deque


# --------------------------------------------------------------------------
# Graph construction
# --------------------------------------------------------------------------
class TaskGraph:
    """Directed graph of tasks. Edge u -> v means u must run before v."""

    def __init__(self):
        self.tasks = []                    # insertion-ordered, no duplicates
        self.adj = defaultdict(list)       # task -> list of dependents
        self._seen = set()

    def add_task(self, task):
        if task not in self._seen:
            self._seen.add(task)
            self.tasks.append(task)

    def add_dependency(self, before, after):
        """Record that `before` must be completed before `after`."""
        self.add_task(before)              # tolerate undeclared tasks
        self.add_task(after)
        if after not in self.adj[before]:  # ignore duplicate edges
            self.adj[before].append(after)


# --------------------------------------------------------------------------
# Input parsing
# --------------------------------------------------------------------------
def parse_lines(lines):
    """Parse the text format described in the module docstring.

    Raises ValueError with the line number when a line cannot be read.
    """
    graph = TaskGraph()
    for lineno, raw in enumerate(lines, 1):
        line = raw.split("#", 1)[0].strip()
        if not line:
            continue
        low = line.lower()
        if low.startswith("tasks:"):
            for name in line.split(":", 1)[1].split(","):
                if name.strip():
                    graph.add_task(name.strip())
        elif low.startswith("dependencies"):
            continue                       # section header
        elif "->" in line:
            parts = [p.strip() for p in line.split("->")]
            if len(parts) != 2 or not all(parts):
                raise ValueError(
                    f"Line {lineno}: malformed dependency '{line}'")
            graph.add_dependency(parts[0], parts[1])
        else:
            raise ValueError(f"Line {lineno}: cannot parse '{line}'")
    if not graph.tasks:
        raise ValueError("No tasks found in input.")
    return graph


def read_interactive():
    """Prompt the user for tasks and dependencies."""
    print("Enter tasks, comma-separated (e.g. A, B, C, D):")
    lines = ["Tasks: " + input("> ")]
    print("Enter dependencies as 'X -> Y' (X before Y), one per line. "
          "Empty line to finish:")
    while True:
        try:
            entry = input("> ").strip()
        except EOFError:                   # Ctrl+D / Ctrl+Z also ends the list
            break
        if not entry:
            break
        lines.append(entry)
    return parse_lines(lines)


# --------------------------------------------------------------------------
# Topological sort (Kahn's algorithm) + cycle detection
# --------------------------------------------------------------------------
def topological_sort(graph):
    """
    Return (order, remaining).
      order     - tasks in a valid execution order (may be partial)
      remaining - tasks never reached; non-empty  <=>  graph has a cycle
    """
    indegree = {t: 0 for t in graph.tasks}
    for u in graph.tasks:
        for v in graph.adj[u]:
            indegree[v] += 1

    # Start with all tasks that have no prerequisites (FIFO keeps the
    # output deterministic and follows input order).
    queue = deque(t for t in graph.tasks if indegree[t] == 0)
    order = []

    while queue:
        u = queue.popleft()
        order.append(u)
        for v in graph.adj[u]:
            indegree[v] -= 1
            if indegree[v] == 0:
                queue.append(v)

    remaining = [t for t in graph.tasks if indegree[t] > 0]
    return order, remaining


def find_cycle(graph, candidates):
    """
    Return one explicit cycle as a list [X, ..., Y, X] using iterative DFS
    restricted to `candidates` (the tasks Kahn's algorithm could not place).
    """
    allowed = set(candidates)
    WHITE, GRAY, BLACK = 0, 1, 2
    color = {t: WHITE for t in allowed}
    parent = {}

    for start in candidates:
        if color[start] != WHITE:
            continue
        stack = [(start, iter(graph.adj[start]))]
        color[start] = GRAY
        while stack:
            node, children = stack[-1]
            advanced = False
            for nxt in children:
                if nxt not in allowed:
                    continue
                if color[nxt] == WHITE:
                    color[nxt] = GRAY
                    parent[nxt] = node
                    stack.append((nxt, iter(graph.adj[nxt])))
                    advanced = True
                    break
                if color[nxt] == GRAY:     # back edge -> cycle found
                    cycle = [nxt]
                    cur = node
                    while cur != nxt:
                        cycle.append(cur)
                        cur = parent[cur]
                    cycle.append(nxt)
                    cycle.reverse()
                    return cycle
            if not advanced:
                color[node] = BLACK
                stack.pop()
    return []


# --------------------------------------------------------------------------
# Main
# --------------------------------------------------------------------------
def solve(graph):
    """Return the result text for a graph."""
    order, remaining = topological_sort(graph)
    if remaining:
        cycle = find_cycle(graph, remaining)
        msg = "Error: Cycle detected. No valid task order."
        if cycle:
            msg += "\nCycle: " + " -> ".join(cycle)
        return msg, False
    return "Valid Task Order: " + " -> ".join(order), True


def main():
    ap = argparse.ArgumentParser(description="Topological task ordering.")
    ap.add_argument("input", nargs="?",
                    help="input file (omit for interactive mode)")
    ap.add_argument("-o", "--output",
                    help="also write the result to this file")
    args = ap.parse_args()

    try:
        if args.input:
            with open(args.input, encoding="utf-8") as f:
                graph = parse_lines(f.readlines())
        else:
            graph = read_interactive()
    except (OSError, ValueError) as exc:
        print(f"Input error: {exc}", file=sys.stderr)
        return 2
    except (EOFError, KeyboardInterrupt):
        print("\nInput cancelled.", file=sys.stderr)
        return 2

    result, ok = solve(graph)
    print(result)
    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(result + "\n")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
