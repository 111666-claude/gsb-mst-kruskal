import io
import unittest
from contextlib import redirect_stdout

from mstk.cli import main
from mstk.mst import GraphError, kruskal, nodes_of, parse_edges


class ParseTest(unittest.TestCase):
    def test_two_edges(self):
        self.assertEqual(parse_edges("a-b:1,c-d:2"), [("a", "b", 1), ("c", "d", 2)])

    def test_missing_colon(self):
        with self.assertRaises(GraphError):
            parse_edges("a-b")

    def test_missing_dash(self):
        with self.assertRaises(GraphError):
            parse_edges("ab:1")


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


if __name__ == "__main__":
    unittest.main()
