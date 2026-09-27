import io
import itertools
import random
import time
import unittest
from contextlib import redirect_stderr, redirect_stdout

from mstk.cli import main
from mstk.mst import GraphError, UnionFind, kruskal, nodes_of, parse_edges


class ParseTest(unittest.TestCase):
    def test_two_edges(self):
        self.assertEqual(parse_edges("a-b:1,c-d:2"), [("a", "b", 1), ("c", "d", 2)])

    def test_strips_whitespace(self):
        self.assertEqual(parse_edges(" a-b : 1 , c-d:2 "), [("a", "b", 1), ("c", "d", 2)])

    def test_missing_colon(self):
        with self.assertRaises(GraphError) as ctx:
            parse_edges("a-b:1,c-d")
        self.assertIn("第 2 条边", ctx.exception.message)

    def test_missing_dash(self):
        with self.assertRaises(GraphError) as ctx:
            parse_edges("ab:1")
        self.assertIn("第 1 条边", ctx.exception.message)

    def test_negative_weight(self):
        with self.assertRaises(GraphError) as ctx:
            parse_edges("a-b:1,b-c:-2")
        self.assertIn("第 2 条边", ctx.exception.message)

    def test_non_numeric_weight(self):
        with self.assertRaises(GraphError) as ctx:
            parse_edges("a-b:x")
        self.assertIn("第 1 条边", ctx.exception.message)

    def test_decimal_weight_rejected(self):
        with self.assertRaises(GraphError):
            parse_edges("a-b:1.5")

    def test_empty_weight_rejected(self):
        with self.assertRaises(GraphError):
            parse_edges("a-b:")

    def test_empty_input(self):
        self.assertEqual(parse_edges(""), [])


class NodesTest(unittest.TestCase):
    def test_first_appearance_order(self):
        self.assertEqual(nodes_of(parse_edges("b-c:1,a-b:2")), ["b", "c", "a"])

    def test_self_loop_still_registers_node(self):
        self.assertEqual(nodes_of(parse_edges("a-a:1")), ["a"])


class UnionFindTest(unittest.TestCase):
    def test_find_walks_to_root_and_compresses(self):
        uf = UnionFind(["a", "b", "c"])
        uf.union("a", "b")
        uf.union("b", "c")
        self.assertEqual(uf.find("a"), uf.find("c"))

    def test_union_detects_cycle(self):
        uf = UnionFind(["a", "b", "c"])
        self.assertTrue(uf.union("a", "b"))
        self.assertTrue(uf.union("b", "c"))
        self.assertFalse(uf.union("a", "c"))

    def test_path_compression(self):
        uf = UnionFind([str(i) for i in range(5)])
        for i in range(4):
            uf.union(str(i), str(i + 1))
        root = uf.find("4")
        uf.find("0")
        self.assertEqual(uf.parent["0"], root)


class KruskalTest(unittest.TestCase):
    def test_single_edge(self):
        total, components, chosen = kruskal(parse_edges("a-b:7"))
        self.assertEqual(total, 7)
        self.assertEqual(components, 1)
        self.assertEqual(chosen, [("a", "b", 7)])

    def test_triangle(self):
        total, components, chosen = kruskal(parse_edges("a-b:1,b-c:1,a-c:1"))
        self.assertEqual(total, 2)
        self.assertEqual(components, 1)
        self.assertEqual(chosen, [("a", "b", 1), ("b", "c", 1)])

    def test_triangle_keeps_two_cheapest(self):
        total, components, chosen = kruskal(parse_edges("a-b:3,b-c:2,a-c:4"))
        self.assertEqual(total, 5)
        self.assertEqual(components, 1)
        self.assertEqual(chosen, [("b", "c", 2), ("a", "b", 3)])

    def test_forest_components(self):
        total, components, chosen = kruskal(parse_edges("a-b:1,c-d:2,e-f:3"))
        self.assertEqual(total, 6)
        self.assertEqual(components, 3)
        self.assertEqual(len(chosen), 3)

    def test_forest_with_a_cycle_component(self):
        total, components, chosen = kruskal(parse_edges("a-b:1,b-c:1,a-c:1,d-e:2"))
        self.assertEqual(total, 4)
        self.assertEqual(components, 2)
        self.assertEqual(len(chosen), 3)

    def test_two_disjoint_edges(self):
        total, components, chosen = kruskal(parse_edges("a-b:1,c-d:2"))
        self.assertEqual(total, 3)
        self.assertEqual(components, 2)
        self.assertEqual(len(chosen), 2)

    def test_self_loop_ignored(self):
        total, components, chosen = kruskal(parse_edges("a-a:9,a-b:1"))
        self.assertEqual(total, 1)
        self.assertEqual(components, 1)
        self.assertEqual(chosen, [("a", "b", 1)])

    def test_self_loop_only(self):
        total, components, chosen = kruskal(parse_edges("a-a:5"))
        self.assertEqual(total, 0)
        self.assertEqual(components, 1)
        self.assertEqual(chosen, [])

    def test_parallel_edges_use_the_cheaper_one(self):
        total, components, chosen = kruskal(parse_edges("a-b:5,a-b:1"))
        self.assertEqual(total, 1)
        self.assertEqual(components, 1)
        self.assertEqual(chosen, [("a", "b", 1)])

    def test_empty(self):
        total, components, chosen = kruskal([])
        self.assertEqual((total, components, chosen), (0, 0, []))

    def test_equal_weights_follow_input_order(self):
        edges = parse_edges("b-c:1,a-c:1,a-b:1")
        total, components, chosen = kruskal(edges)
        self.assertEqual(total, 2)
        self.assertEqual(components, 1)
        self.assertEqual(chosen, [("b", "c", 1), ("a", "c", 1)])

    def test_repeated_runs_are_identical(self):
        edges = parse_edges("a-b:2,b-c:1,c-d:1,a-c:2,b-d:3")
        first = kruskal(edges)
        for _ in range(20):
            self.assertEqual(kruskal(edges), first)

    def test_chosen_edges_never_form_a_cycle(self):
        edges = parse_edges("a-b:1,b-c:1,c-d:1,d-a:1,a-c:5,b-d:6")
        _total, _components, chosen = kruskal(edges)
        uf = UnionFind(nodes_of(edges))
        for left, right, _weight in chosen:
            self.assertTrue(uf.union(left, right))

    def test_invariants(self):
        edges = parse_edges("a-b:2,b-c:3,c-d:1,a-c:4,e-f:2,f-g:2,e-g:7,g-g:1")
        total, components, chosen = kruskal(edges)
        node_count = len(nodes_of(edges))
        self.assertEqual(total, sum(weight for _l, _r, weight in chosen))
        self.assertEqual(components, node_count - len(chosen))
        uf = UnionFind(nodes_of(edges))
        for left, right, _weight in chosen:
            self.assertTrue(uf.union(left, right))


def brute_force_msf(edges):
    """枚举所有边子集，取无环且边数最多的子集里权重最小的（即最小生成森林）。"""
    nodes = nodes_of(edges)
    non_loops = [(l, r, w) for l, r, w in edges if l != r]
    # 森林边数的上界：节点数 - 连通分量数；逐子集枚举时按边数最大化判定。
    best_weight = None
    best_count = -1
    for size in range(len(non_loops), -1, -1):
        if size < best_count:
            break
        for subset in itertools.combinations(non_loops, size):
            uf = UnionFind(nodes)
            weight = 0
            ok = True
            for left, right, edge_weight in subset:
                if not uf.union(left, right):
                    ok = False
                    break
                weight += edge_weight
            if ok and size > best_count:
                best_count = size
                best_weight = weight
            elif ok and size == best_count and (best_weight is None or weight < best_weight):
                best_weight = weight
        if best_count == len(nodes) - 1 or best_count == len(non_loops):
            break
    return best_weight if best_weight is not None else 0


class BruteForceCrossCheckTest(unittest.TestCase):
    def test_random_small_graphs(self):
        rng = random.Random(20260927)
        for _ in range(60):
            n = rng.randint(1, 8)
            node_names = ["v%d" % i for i in range(n)]
            m = rng.randint(0, 12)
            edges = []
            for _ in range(m):
                left = rng.choice(node_names)
                right = rng.choice(node_names)
                edges.append((left, right, rng.randint(0, 9)))
            total, components, chosen = kruskal(edges)
            self.assertEqual(total, brute_force_msf(edges))
            self.assertEqual(components, len(nodes_of(edges)) - len(chosen))
            self.assertEqual(total, sum(w for _l, _r, w in chosen))


class PerformanceTest(unittest.TestCase):
    def test_large_graph_under_three_seconds(self):
        rng = random.Random(7)
        n = 50_000
        edges = []
        for i in range(n - 1):
            edges.append(("v%d" % i, "v%d" % (i + 1), rng.randint(0, 1000)))
        for _ in range(200_000 - len(edges)):
            left = rng.randrange(n)
            right = rng.randrange(n)
            edges.append(("v%d" % left, "v%d" % right, rng.randint(0, 1000)))
        start = time.perf_counter()
        total, components, chosen = kruskal(edges)
        elapsed = time.perf_counter() - start
        self.assertLess(elapsed, 3.0)
        self.assertEqual(components, 1)
        self.assertEqual(len(chosen), n - 1)
        self.assertEqual(total, sum(w for _l, _r, w in chosen))


class CliTest(unittest.TestCase):
    def test_prints_total(self):
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            code = main(["--edges", "a-b:3"])
        self.assertEqual(code, 0)
        lines = buffer.getvalue().split()
        self.assertEqual(lines[0], "total=3")
        self.assertEqual(lines[1], "components=1")
        self.assertEqual(lines[2], "edges=a-b(3)")

    def test_triangle_output(self):
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            code = main(["--edges", "a-b:1,b-c:1,a-c:1"])
        self.assertEqual(code, 0)
        self.assertEqual(
            buffer.getvalue().splitlines(),
            ["total=2", "components=1", "edges=a-b(1),b-c(1)"],
        )

    def test_empty_edges_outputs_empty_forest(self):
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            code = main(["--edges", ""])
        self.assertEqual(code, 0)
        self.assertEqual(
            buffer.getvalue().splitlines(),
            ["total=0", "components=0", "edges="],
        )

    def test_missing_edges(self):
        self.assertEqual(main([]), 2)

    def test_invalid_input_reports_index_and_fails(self):
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = main(["--edges", "a-b:1,b-c:x,c-d:2"])
        self.assertEqual(code, 1)
        self.assertIn("第 2 条边", err.getvalue())
        self.assertEqual(out.getvalue(), "")


if __name__ == "__main__":
    unittest.main()
