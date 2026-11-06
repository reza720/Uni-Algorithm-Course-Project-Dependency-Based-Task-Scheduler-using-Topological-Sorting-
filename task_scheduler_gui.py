#!/usr/bin/env python3
"""
task_scheduler_gui.py - Tkinter GUI for the topological-sort task scheduler.

Requires task_scheduler.py in the same folder (it reuses its parser, Kahn's
algorithm and cycle finder). Only the Python standard library is used.

Algorithms, Fall 2026, Section 001 - Final Project (AUAF)
GUI: Sweeta Latifi. Revisions: Ehsanullah Naseri.

Run:  python task_scheduler_gui.py

Features
  * Type tasks and dependencies, or load an input file.
  * "Find Order" (or Ctrl+Enter) shows the valid order, or the cycle error.
  * The graph is drawn: layered left-to-right for a valid DAG; arranged in
    a circle with the cycle highlighted in red when a cycle exists.
  * Node size follows the task name, and an arrow that would cross another
    task is drawn as a curve around it.
"""

import math
import os
import tkinter as tk
import tkinter.font as tkfont
from tkinter import filedialog, messagebox, ttk

import task_scheduler as ts

EXAMPLE_TASKS = "A, B, C, D"
EXAMPLE_DEPS = "A -> B\nB -> C\nC -> D"

NODE_R = 20                 # node half-height (and minimum half-width)
NODE_PAD = 12               # space between a task name and the node outline
TITLE = "Task Scheduler - Topological Sort"
COL_NODE = "#dbe8f7"
COL_NODE_OK = "#d4edda"
COL_NODE_BAD = "#f8d7da"
COL_EDGE = "#555555"
COL_CYCLE = "#c0392b"


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(TITLE)
        self.geometry("980x600")
        self.minsize(820, 500)

        self.graph = None
        self.order = []
        self.cycle = []
        self.last_result = ""
        self.label_font = tkfont.Font(family="Segoe UI", size=10,
                                      weight="bold")

        self._build_ui()
        self.load_example()

    # ------------------------------------------------------------------ UI
    def _build_ui(self):
        left = ttk.Frame(self, padding=10)
        left.pack(side=tk.LEFT, fill=tk.Y)
        right = ttk.Frame(self, padding=(0, 10, 10, 10))
        right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        ttk.Label(left, text="Tasks (comma-separated)").pack(anchor="w")
        self.tasks_var = tk.StringVar()
        ttk.Entry(left, textvariable=self.tasks_var, width=36).pack(
            fill=tk.X, pady=(2, 10))

        ttk.Label(left, text="Dependencies (one per line: X -> Y,\n"
                             "X must be done before Y)").pack(anchor="w")
        self.deps_text = tk.Text(left, width=36, height=14, wrap="none",
                                 font=("Consolas", 11))
        self.deps_text.pack(fill=tk.BOTH, expand=True, pady=(2, 10))

        row1 = ttk.Frame(left)
        row1.pack(fill=tk.X, pady=2)
        ttk.Button(row1, text="Find Order", command=self.run).pack(
            side=tk.LEFT, expand=True, fill=tk.X, padx=(0, 3))
        ttk.Button(row1, text="Clear", command=self.clear).pack(
            side=tk.LEFT, expand=True, fill=tk.X, padx=(3, 0))

        row2 = ttk.Frame(left)
        row2.pack(fill=tk.X, pady=2)
        ttk.Button(row2, text="Load File...", command=self.load_file).pack(
            side=tk.LEFT, expand=True, fill=tk.X, padx=(0, 3))
        ttk.Button(row2, text="Save Result...", command=self.save_result).pack(
            side=tk.LEFT, expand=True, fill=tk.X, padx=(3, 0))

        ttk.Button(left, text="Load Example", command=self.load_example).pack(
            fill=tk.X, pady=2)

        self.canvas = tk.Canvas(right, bg="white", highlightthickness=1,
                                highlightbackground="#bbbbbb")
        self.canvas.pack(fill=tk.BOTH, expand=True)
        self.canvas.bind("<Configure>", lambda e: self.draw())

        self.result_var = tk.StringVar(value="Press 'Find Order'.")
        self.result_lbl = tk.Label(right, textvariable=self.result_var,
                                   anchor="w", justify="left", wraplength=640,
                                   font=("Segoe UI", 11, "bold"), pady=8)
        self.result_lbl.pack(fill=tk.X)
        # keep long orders inside the window instead of cutting them off
        right.bind("<Configure>", lambda e: self.result_lbl.config(
            wraplength=max(200, e.width - 20)))

        # Ctrl+Enter = Find Order. Bound on the text box itself as well so
        # the key press runs the scheduler without adding a new line.
        self.deps_text.bind("<Control-Return>", self._shortcut_run)
        self.bind_all("<Control-Return>", self._shortcut_run)

    def _shortcut_run(self, _event=None):
        self.run()
        return "break"

    # ------------------------------------------------------------- actions
    def _input_lines(self):
        lines = ["Tasks: " + self.tasks_var.get()]
        lines += self.deps_text.get("1.0", tk.END).splitlines()
        return lines

    def run(self):
        try:
            self.graph = ts.parse_lines(self._input_lines())
        except ValueError as exc:
            messagebox.showerror("Input error", str(exc))
            return

        self.order, remaining = ts.topological_sort(self.graph)
        if remaining:
            self.cycle = ts.find_cycle(self.graph, remaining)
            self.order = []
            text = "Error: Cycle detected. No valid task order."
            if self.cycle:
                text += "\nCycle: " + " -> ".join(self.cycle)
            self.result_lbl.config(fg=COL_CYCLE)
        else:
            self.cycle = []
            text = "Valid Task Order: " + " -> ".join(self.order)
            self.result_lbl.config(fg="#1e7e34")
        self.last_result = text
        self.result_var.set(text)
        self.draw()

    def clear(self):
        self.tasks_var.set("")
        self.deps_text.delete("1.0", tk.END)
        self.graph, self.order, self.cycle = None, [], []
        self.last_result = ""
        self.result_lbl.config(fg="black")
        self.result_var.set("Press 'Find Order'.")
        self.title(TITLE)
        self.draw()

    def load_example(self):
        self.clear()
        self.tasks_var.set(EXAMPLE_TASKS)
        self.deps_text.insert("1.0", EXAMPLE_DEPS)

    def load_file(self):
        path = filedialog.askopenfilename(
            title="Open input file",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")])
        if not path:
            return
        try:
            with open(path, encoding="utf-8") as f:
                lines = f.read().splitlines()
        except OSError as exc:
            messagebox.showerror("File error", str(exc))
            return

        tasks, deps = [], []
        for line in lines:
            clean = line.split("#", 1)[0].strip()
            low = clean.lower()
            if not clean or low.startswith("dependencies"):
                continue
            if low.startswith("tasks:"):
                tasks.append(clean.split(":", 1)[1].strip())
            else:
                deps.append(clean)
        self.clear()
        self.tasks_var.set(", ".join(tasks))
        self.deps_text.insert("1.0", "\n".join(deps))
        self.title(f"{TITLE} - {os.path.basename(path)}")
        self.run()

    def save_result(self):
        if not self.last_result:
            messagebox.showinfo("Nothing to save", "Run 'Find Order' first.")
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".txt", filetypes=[("Text files", "*.txt")])
        if path:
            with open(path, "w", encoding="utf-8") as f:
                f.write(self.last_result + "\n")

    # ------------------------------------------------------------- drawing
    def _node_size(self, task):
        """Half-width and half-height of the ellipse drawn for a task."""
        half_text = self.label_font.measure(task) / 2
        return max(NODE_R, half_text + NODE_PAD), NODE_R

    def _layout(self, w, h):
        """Return {task: (x, y)} positions for the current graph."""
        g = self.graph
        pos = {}
        if self.order:                       # DAG -> layered, left to right
            depth = {t: 0 for t in g.tasks}
            has_pred = set()
            for u in self.order:
                for v in g.adj[u]:
                    depth[v] = max(depth[v], depth[u] + 1)
                    has_pred.add(v)
            # A task with no prerequisites is drawn just before the first
            # task that needs it, so its arrow stays short.
            for t in g.tasks:
                if t not in has_pred and g.adj[t]:
                    depth[t] = min(depth[v] for v in g.adj[t]) - 1
            layers = {}
            for t in g.tasks:
                layers.setdefault(depth[t], []).append(t)
            n_layers = max(layers) + 1
            self._order_layers(layers, n_layers)

            # Column width follows the widest task name in that column;
            # the remaining space is shared out evenly between columns.
            col_w = [max(2 * self._node_size(t)[0] for t in layers[d])
                     for d in range(n_layers)]
            gap = max(8, (w - 20 - sum(col_w)) / n_layers)
            x = 10
            for d in range(n_layers):
                cx = x + gap / 2 + col_w[d] / 2
                x += col_w[d] + gap
                members = layers[d]
                for i, t in enumerate(members):
                    pos[t] = (cx, h * (i + 1) / (len(members) + 1))
        else:                                # cycle (or unsorted) -> circle
            n = len(g.tasks)
            cx, cy = w / 2, h / 2
            r = max(40, min(w, h) / 2 - 50)
            for i, t in enumerate(g.tasks):
                a = 2 * math.pi * i / n - math.pi / 2
                pos[t] = (cx + r * math.cos(a), cy + r * math.sin(a))
        return pos

    def _order_layers(self, layers, n_layers):
        """Reorder tasks inside each layer to reduce crossing arrows.

        Barycenter heuristic: a task is placed near the average vertical
        position of the tasks it is connected to in the neighbouring layers.
        Two sweeps (left-to-right, then right-to-left) are enough here.
        """
        preds = {t: [] for ts in layers.values() for t in ts}
        for u in preds:
            for v in self.graph.adj[u]:
                preds[v].append(u)

        def rank(t):
            for members in layers.values():
                if t in members:
                    return (members.index(t) + 1) / (len(members) + 1)
            return 0.5

        def sweep(depths, neighbours):
            for d in depths:
                members = layers[d]
                if len(members) < 2:
                    continue
                keys = {}
                for i, t in enumerate(members):
                    near = neighbours(t)
                    keys[t] = (sum(rank(n) for n in near) / len(near)
                               if near else (i + 1) / (len(members) + 1))
                members.sort(key=lambda t: keys[t])

        sweep(range(1, n_layers), lambda t: preds[t])
        sweep(range(n_layers - 2, -1, -1), lambda t: self.graph.adj[t])

    @staticmethod
    def _edge_point(center, size, toward):
        """Point on an ellipse outline in the direction of `toward`."""
        dx, dy = toward[0] - center[0], toward[1] - center[1]
        dist = math.hypot(dx, dy) or 1.0
        ux, uy = dx / dist, dy / dist
        rx, ry = size
        t = 1.0 / math.sqrt((ux / rx) ** 2 + (uy / ry) ** 2)
        return center[0] + ux * t, center[1] + uy * t

    def _hits(self, p, ctrl, q, others, pos, sizes):
        """How many other nodes the (curved) edge p -> ctrl -> q touches."""
        count = 0
        for t in others:
            (cx, cy), (rx, ry) = pos[t], sizes[t]
            for k in range(1, 20):
                s = k / 20                   # point on the Bezier curve
                a, b, c = (1 - s) ** 2, 2 * (1 - s) * s, s * s
                x = a * p[0] + b * ctrl[0] + c * q[0]
                y = a * p[1] + b * ctrl[1] + c * q[1]
                if ((x - cx) / (rx + 6)) ** 2 + ((y - cy) / (ry + 6)) ** 2 < 1:
                    count += 1
                    break
        return count

    def _arrow(self, u, v, pos, sizes, color, width):
        c = self.canvas
        p, q = pos[u], pos[v]
        if u == v:                           # self-loop: small outward arc
            x, y = p
            w, h = c.winfo_width(), c.winfo_height()
            ox, oy = x - w / 2, y - h / 2
            d = math.hypot(ox, oy)
            ox, oy = (ox / d, oy / d) if d > 1 else (0.0, -1.0)
            ex, ey = self._edge_point(p, sizes[u], (x + ox, y + oy))
            b = math.hypot(ex - x, ey - y)   # distance to the outline
            px, py = -oy, ox                 # perpendicular to outward dir

            def at(along, side):
                return (x + ox * along + px * side,
                        y + oy * along + py * side)

            pts = [at(b - 2, -8), at(b + 34, -24),
                   at(b + 34, 24), at(b - 2, 8)]
            c.create_line(*[k for pt in pts for k in pt], smooth=True,
                          arrow=tk.LAST, fill=color, width=width,
                          arrowshape=(10, 12, 4))
            return

        dx, dy = q[0] - p[0], q[1] - p[1]
        dist = math.hypot(dx, dy) or 1.0
        nx, ny = -dy / dist, dx / dist       # unit normal to the edge
        mid = ((p[0] + q[0]) / 2, (p[1] + q[1]) / 2)
        others = [t for t in pos if t not in (u, v)]

        # A pair A -> B and B -> A would overlap as straight lines, so each
        # one is bent to its own side. Otherwise prefer a straight arrow and
        # bend it only when it would pass through another task.
        two_way = u in self.graph.adj[v]
        offsets = [28, 60] if two_way else [0, 40, -40, 75, -75, 110, -110]
        best = None
        for off in offsets:
            ctrl = (mid[0] + nx * off, mid[1] + ny * off)
            hits = self._hits(p, ctrl, q, others, pos, sizes)
            if best is None or hits < best[0]:
                best = (hits, ctrl)
            if hits == 0:
                break
        ctrl = best[1]

        start = self._edge_point(p, sizes[u], ctrl)
        end = self._edge_point(q, sizes[v], ctrl)
        c.create_line(start[0], start[1], ctrl[0], ctrl[1], end[0], end[1],
                      smooth=True, arrow=tk.LAST, fill=color, width=width,
                      arrowshape=(10, 12, 4))

    def draw(self):
        c = self.canvas
        c.delete("all")
        if not self.graph or not self.graph.tasks:
            c.create_text(c.winfo_width() / 2, c.winfo_height() / 2,
                          text="Enter tasks and dependencies, then press "
                               "Find Order.",
                          fill="#888888", font=("Segoe UI", 10))
            return
        w, h = c.winfo_width(), c.winfo_height()
        pos = self._layout(w, h)
        sizes = {t: self._node_size(t) for t in pos}

        cycle_edges = set(zip(self.cycle, self.cycle[1:]))
        cycle_nodes = set(self.cycle)

        # normal edges first, so the red cycle is drawn on top of them
        edges = [(u, v) for u in self.graph.tasks for v in self.graph.adj[u]]
        edges.sort(key=lambda e: e in cycle_edges)
        for u, v in edges:
            bad = (u, v) in cycle_edges
            self._arrow(u, v, pos, sizes,
                        COL_CYCLE if bad else COL_EDGE, 3 if bad else 1.5)

        step = {t: i + 1 for i, t in enumerate(self.order)}
        for t, (x, y) in pos.items():
            if t in cycle_nodes:
                fill, outline = COL_NODE_BAD, COL_CYCLE
            elif step:
                fill, outline = COL_NODE_OK, "#2e7d32"
            else:
                fill, outline = COL_NODE, "#4a76a8"
            rx, ry = sizes[t]
            c.create_oval(x - rx, y - ry, x + rx, y + ry,
                          fill=fill, outline=outline, width=2)
            c.create_text(x, y, text=t, font=self.label_font)
            if t in step:                    # execution step number
                c.create_text(x, y + ry + 10, text=f"#{step[t]}",
                              fill="#1e7e34", font=("Segoe UI", 9))


if __name__ == "__main__":
    App().mainloop()
