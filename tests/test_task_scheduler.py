"""
Test cases for task_scheduler.py (Cycle Checker & Tester module).

Run from the topo_sort folder:
    python -m unittest discover -s tests -v

Only the standard library is used.
"""

import os
import random
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SAMPLES = os.path.join(ROOT, "samples")
sys.path.insert(0, ROOT)

import task_scheduler as ts  # noqa: E402


def build(text):
    return ts.parse_lines(text.strip().splitlines())


def respects_all_edges(graph, order):
    """True if every task appears once and each u -> v has u before v."""
    if sorted(order) != sorted(graph.tasks):
        return False
    where = {t: i for i, t in enumerate(order)}
    return all(where[u] < where[v] for u in graph.tasks for v in graph.adj[u])


def is_real_cycle(graph, cycle):
    """True if cycle = [X, ..., X] and every step is an actual edge."""
    if len(cycle) < 2 or cycle[0] != cycle[-1]:
        return False
    return all(b in graph.adj[a] for a, b in zip(cycle, cycle[1:]))


class ParserTests(unittest.TestCase):

    def test_sample_format(self):
        g = build("Tasks: A, B, C, D\nDependencies:\nA -> B\nB -> C\nC -> D")
        self.assertEqual(g.tasks, ["A", "B", "C", "D"])
        self.assertEqual(g.adj["A"], ["B"])

    def test_comments_and_blank_lines_are_ignored(self):
        g = build("# header\n\nTasks: A, B   # two tasks\n\nA -> B  # edge")
        self.assertEqual(g.tasks, ["A", "B"])
        self.assertEqual(g.adj["A"], ["B"])

    def test_undeclared_task_is_added(self):
        g = build("Tasks: A\nA -> Z")
        self.assertEqual(g.tasks, ["A", "Z"])

    def test_duplicates_are_ignored(self):
        g = build("Tasks: A, B, A\nA -> B\nA -> B")
        self.assertEqual(g.tasks, ["A", "B"])
        self.assertEqual(g.adj["A"], ["B"])

    def test_names_with_spaces_and_no_spaces_around_arrow(self):
        g = build("Tasks: Write code, Run tests\nWrite code->Run tests")
        self.assertEqual(g.adj["Write code"], ["Run tests"])

    def test_dependencies_only_without_tasks_line(self):
        g = build("A -> B\nB -> C")
        self.assertEqual(g.tasks, ["A", "B", "C"])

    def test_malformed_lines_report_line_number(self):
        for bad in ["A => B", "A ->", "-> B", "A -> B -> C", "just text"]:
            with self.subTest(line=bad):
                with self.assertRaisesRegex(ValueError, "Line 2"):
                    build("Tasks: A, B\n" + bad)

    def test_empty_input_is_rejected(self):
        with self.assertRaises(ValueError):
            ts.parse_lines(["", "# only a comment", "Dependencies:"])


class TopologicalSortTests(unittest.TestCase):

    def test_assignment_sample(self):
        g = build("Tasks: A, B, C, D\nA -> B\nB -> C\nC -> D")
        self.assertEqual(ts.solve(g),
                         ("Valid Task Order: A -> B -> C -> D", True))

    def test_order_does_not_depend_on_line_order(self):
        g = build("Tasks: A, B, C, D\nC -> D\nB -> C\nA -> B")
        order, remaining = ts.topological_sort(g)
        self.assertEqual(order, ["A", "B", "C", "D"])
        self.assertEqual(remaining, [])

    def test_independent_tasks_keep_input_order(self):
        g = build("Tasks: P, Q, R")
        self.assertEqual(ts.topological_sort(g)[0], ["P", "Q", "R"])

    def test_diamond_and_disconnected_parts(self):
        g = build("Tasks: A, B, C, D, X, Y\nA -> B\nA -> C\nB -> D\nC -> D\n"
                  "X -> Y")
        order, remaining = ts.topological_sort(g)
        self.assertFalse(remaining)
        self.assertTrue(respects_all_edges(g, order))

    def test_single_task(self):
        self.assertEqual(ts.solve(build("Tasks: Only")),
                         ("Valid Task Order: Only", True))

    def test_random_dags_give_valid_orders(self):
        rng = random.Random(366)
        for _ in range(200):
            n = rng.randint(1, 40)
            names = [f"T{i}" for i in range(n)]
            rng.shuffle(names)
            # edges only go forward in `names`, so the graph is acyclic
            lines = ["Tasks: " + ", ".join(sorted(names))]
            for i in range(n):
                for j in range(i + 1, n):
                    if rng.random() < 0.15:
                        lines.append(f"{names[i]} -> {names[j]}")
            g = ts.parse_lines(lines)
            order, remaining = ts.topological_sort(g)
            self.assertFalse(remaining)
            self.assertTrue(respects_all_edges(g, order))

    def test_long_chain_has_no_recursion_problem(self):
        n = 100_000
        lines = [f"T{i} -> T{i + 1}" for i in range(n)]
        g = ts.parse_lines(lines)
        order, remaining = ts.topological_sort(g)
        self.assertEqual(len(order), n + 1)
        self.assertEqual(order[0], "T0")
        self.assertEqual(order[-1], f"T{n}")


class CycleDetectionTests(unittest.TestCase):

    def assert_cycle(self, text, expected=None):
        g = build(text)
        result, ok = ts.solve(g)
        self.assertFalse(ok)
        self.assertTrue(result.startswith(
            "Error: Cycle detected. No valid task order."))
        _, remaining = ts.topological_sort(g)
        cycle = ts.find_cycle(g, remaining)
        self.assertTrue(is_real_cycle(g, cycle), cycle)
        if expected:
            self.assertEqual(cycle, expected)
        return cycle

    def test_assignment_cycle_sample(self):
        self.assert_cycle("Tasks: A, B, C, D\nA -> B\nB -> C\nC -> D\nD -> B",
                          ["B", "C", "D", "B"])

    def test_two_task_cycle(self):
        self.assert_cycle("A -> B\nB -> A", ["A", "B", "A"])

    def test_self_dependency(self):
        self.assert_cycle("Tasks: A, B\nA -> B\nB -> B", ["B", "B"])

    def test_cycle_with_tasks_before_and_after_it(self):
        # S and E are not on the cycle; the reported cycle must not include
        # them even though Kahn's algorithm leaves E unprocessed too.
        cycle = self.assert_cycle("S -> A\nA -> B\nB -> C\nC -> A\nC -> E")
        self.assertNotIn("S", cycle)
        self.assertNotIn("E", cycle)

    def test_downstream_task_listed_first(self):
        # E comes first in the task list but is only *behind* the cycle.
        self.assert_cycle("Tasks: E, A, B\nA -> B\nB -> A\nB -> E")

    def test_valid_part_does_not_hide_cycle(self):
        self.assert_cycle("A -> B\nB -> C\nX -> Y\nY -> Z\nZ -> X")

    def test_random_graphs_with_one_back_edge(self):
        rng = random.Random(49783)
        for _ in range(200):
            n = rng.randint(2, 30)
            lines = [f"N{i} -> N{i + 1}" for i in range(n - 1)]
            i = rng.randrange(n)
            j = rng.randrange(i + 1)          # j <= i closes a cycle
            lines.append(f"N{i} -> N{j}")
            rng.shuffle(lines)
            self.assert_cycle("\n".join(lines))


class SampleFileTests(unittest.TestCase):
    """Every samples/inputN_*.txt must produce samples/outputN.txt."""

    def test_sample_outputs_match(self):
        checked = 0
        for name in sorted(os.listdir(SAMPLES)):
            if not name.startswith("input"):
                continue
            number = name[len("input"):].split("_")[0]
            expected_path = os.path.join(SAMPLES, f"output{number}.txt")
            with open(expected_path, encoding="utf-8") as f:
                expected = f.read().strip()
            with open(os.path.join(SAMPLES, name), encoding="utf-8") as f:
                lines = f.readlines()
            with self.subTest(sample=name):
                try:
                    actual = ts.solve(ts.parse_lines(lines))[0]
                except ValueError as exc:
                    actual = f"Input error: {exc}"
                self.assertEqual(actual, expected)
            checked += 1
        self.assertGreaterEqual(checked, 3)


class CommandLineTests(unittest.TestCase):

    def run_cli(self, *args, stdin=""):
        return subprocess.run(
            [sys.executable, os.path.join(ROOT, "task_scheduler.py"), *args],
            input=stdin, capture_output=True, text=True, timeout=30)

    def test_exit_codes(self):
        cases = [("input1_valid.txt", 0), ("input2_cycle.txt", 1),
                 ("input6_bad_format.txt", 2)]
        for name, code in cases:
            with self.subTest(sample=name):
                proc = self.run_cli(os.path.join(SAMPLES, name))
                self.assertEqual(proc.returncode, code)

    def test_output_file_option(self):
        out = os.path.join(tempfile.mkdtemp(), "result.txt")
        self.run_cli(os.path.join(SAMPLES, "input1_valid.txt"), "-o", out)
        with open(out, encoding="utf-8") as f:
            self.assertEqual(f.read(), "Valid Task Order: A -> B -> C -> D\n")

    def test_missing_file(self):
        proc = self.run_cli("does_not_exist.txt")
        self.assertEqual(proc.returncode, 2)
        self.assertIn("Input error", proc.stderr)

    def test_interactive_mode(self):
        proc = self.run_cli(stdin="A, B, C\nC -> A\nA -> B\n\n")
        self.assertEqual(proc.returncode, 0)
        self.assertIn("Valid Task Order: C -> A -> B", proc.stdout)


if __name__ == "__main__":
    unittest.main()
