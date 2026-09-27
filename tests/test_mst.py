import io
import itertools
import random
import time
import unittest
from contextlib import redirect_stdout

from mstk.cli import main
from mstk.mst import GraphError, UnionFind, kruskal, nodes_of, parse_edges


class ParseTest(unittest.TestCase):
    def test_two_edges(self):
        self.assertEqual(parse_edges("a-b:1,c-d:2"), [("a", "b", 1), ("c", "d", 2)])

    def test_missing_colon(self):
        with self.assertRaises(GraphError):
            parse_edges("a-b")

    def test_missing_dash(self):
        with self.assertRaises(GraphError):
            parse_edges("ab:1")

    def test_error_reports_edge_index(self):
        with self.assertRaises(GraphError) as caught:
            parse_edges("a-b:1,c-d")
        self.assertIn("第 2 条边", str(caught.exception))

    def test_negative_weight_rejected(self):
        with self.assertRaises(GraphError) as caught:
            parse_edges("a-b:-3")
        self.assertIn("第 1 条边", str(caught.exception))

    def test_non_numeric_weight_rejected(self):
        for bad in ("a-b:x", "a-b:1.5", "a-b:1x", "a-b:"):
            with self.assertRaises(GraphError, msg=bad):
                parse_edges(bad)

    def test_zero_weight_allowed(self):
        self.assertEqual(parse_edges("a-b:0"), [("a", "b", 0)])


class UnionFindTest(unittest.TestCase):
    def test_find_walks_to_root_and_compresses(self):
        forest = UnionFind(["a", "b", "c", "d"])
        forest.union("a", "b")
        forest.union("b", "c")
        forest.union("c", "d")
        root = forest.find("a")
        self.assertEqual(root, forest.find("d"))
        for node in ("a", "b", "c", "d"):
            self.assertEqual(forest.parent[node], root)

    def test_union_detects_cycle(self):
        forest = UnionFind(["a", "b", "c"])
        self.assertTrue(forest.union("a", "b"))
        self.assertTrue(forest.union("b", "c"))
        self.assertFalse(forest.union("a", "c"))


class NodesTest(unittest.TestCase):
    def test_first_appearance_order(self):
        self.assertEqual(nodes_of(parse_edges("b-c:1,a-b:2")), ["b", "c", "a"])


class KruskalTest(unittest.TestCase):
    def test_single_edge(self):
        total, _, chosen = kruskal(parse_edges("a-b:7"))
        self.assertEqual(total, 7)
        self.assertEqual(chosen, [("a", "b", 7)])

    def test_two_disjoint_edges(self):
        total, _, chosen = kruskal(parse_edges("a-b:1,c-d:2"))
        self.assertEqual(total, 3)
        self.assertEqual(len(chosen), 2)

    def test_self_loop_ignored(self):
        total, _, chosen = kruskal(parse_edges("a-a:9,a-b:1"))
        self.assertEqual(total, 1)
        self.assertEqual(chosen, [("a", "b", 1)])

    def test_parallel_edges_use_the_cheaper_one(self):
        total, _, chosen = kruskal(parse_edges("a-b:5,a-b:1"))
        self.assertEqual(total, 1)
        self.assertEqual(chosen, [("a", "b", 1)])

    def test_empty(self):
        total, components, chosen = kruskal([])
        self.assertEqual((total, components, chosen), (0, 0, []))

    def test_triangle_drops_cycle_edge(self):
        total, components, chosen = kruskal(parse_edges("a-b:1,b-c:1,a-c:1"))
        self.assertEqual(total, 2)
        self.assertEqual(components, 1)
        self.assertEqual(chosen, [("a", "b", 1), ("b", "c", 1)])

    def test_triangle_picks_cheapest_two(self):
        total, components, chosen = kruskal(parse_edges("a-b:1,b-c:2,a-c:3"))
        self.assertEqual(total, 3)
        self.assertEqual(components, 1)
        self.assertEqual(chosen, [("a", "b", 1), ("b", "c", 2)])

    def test_forest_components(self):
        total, components, chosen = kruskal(parse_edges("a-b:1,c-d:2,e-f:3"))
        self.assertEqual(total, 6)
        self.assertEqual(components, 3)
        self.assertEqual(len(chosen), 3)

    def test_components_equals_nodes_minus_chosen(self):
        _, components, chosen = kruskal(parse_edges("a-b:1,b-c:1,a-c:1,d-e:2"))
        self.assertEqual(components, 5 - len(chosen))
        self.assertEqual(components, 2)

    def test_equal_weights_keep_input_order(self):
        _, _, chosen = kruskal(parse_edges("c-d:1,a-b:1,b-c:1"))
        self.assertEqual(chosen, [("c", "d", 1), ("a", "b", 1), ("b", "c", 1)])

    def test_deterministic_across_runs(self):
        edges = parse_edges("a-b:1,b-c:1,a-c:1,c-d:2,d-a:2,b-d:3")
        first = kruskal(edges)
        for _ in range(5):
            self.assertEqual(kruskal(edges), first)


def brute_force_forest_total(edges):
    """枚举所有边子集，取无环且权重最小的森林的总权重。"""
    real_edges = [(u, v, w) for u, v, w in edges if u != v]
    best = None
    for size in range(len(real_edges), -1, -1):
        for subset in itertools.combinations(real_edges, size):
            nodes = nodes_of(subset)
            forest = UnionFind(nodes)
            if all(forest.union(u, v) for u, v, _ in subset):
                total = sum(w for _, _, w in subset)
                if best is None or total < best:
                    best = total
        if best is not None:
            return best
    return 0


class BruteForceCrossCheckTest(unittest.TestCase):
    def test_matches_brute_force_on_random_small_graphs(self):
        rng = random.Random(20260927)
        for _ in range(60):
            node_count = rng.randint(1, 8)
            nodes = [str(i) for i in range(node_count)]
            edge_count = rng.randint(0, 12)
            edges = []
            for _ in range(edge_count):
                left = rng.choice(nodes)
                right = rng.choice(nodes)
                edges.append((left, right, rng.randint(0, 9)))
            total, components, chosen = kruskal(edges)
            self.assertEqual(total, brute_force_forest_total(edges), edges)
            distinct = nodes_of(edges)
            self.assertEqual(components, len(distinct) - len(chosen), edges)


class ScaleTest(unittest.TestCase):
    def test_50k_nodes_200k_edges_under_3_seconds(self):
        rng = random.Random(7)
        node_count, edge_count = 50000, 200000
        edges = [
            (str(rng.randrange(node_count)), str(rng.randrange(node_count)),
             rng.randint(0, 1000))
            for _ in range(edge_count)
        ]
        start = time.perf_counter()
        total, components, chosen = kruskal(edges)
        elapsed = time.perf_counter() - start
        self.assertLess(elapsed, 3.0)
        self.assertEqual(total, sum(w for _, _, w in chosen))
        self.assertEqual(components, len(nodes_of(edges)) - len(chosen))


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

    def test_missing_edges(self):
        self.assertEqual(main([]), 2)

    def test_triangle_output(self):
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            code = main(["--edges", "a-b:1,b-c:1,a-c:1"])
        self.assertEqual(code, 0)
        self.assertEqual(
            buffer.getvalue().splitlines(),
            ["total=2", "components=1", "edges=a-b(1),b-c(1)"],
        )

    def test_empty_edges_value(self):
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            code = main(["--edges", ""])
        self.assertEqual(code, 0)
        self.assertEqual(
            buffer.getvalue().splitlines(), ["total=0", "components=0", "edges="]
        )

    def test_invalid_input_reports_index(self):
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            code = main(["--edges", "a-b:1,c-d"])
        self.assertEqual(code, 1)


if __name__ == "__main__":
    unittest.main()
