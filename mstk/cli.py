"""命令行入口：打印最小生成森林的总权重、分量数与选中的边。"""

import argparse
import sys

from .mst import GraphError, kruskal, parse_edges


def build_parser():
    parser = argparse.ArgumentParser(prog="mst-kruskal", description="Kruskal 最小生成森林")
    parser.add_argument("--edges", help="逗号分隔的 u-v:权重")
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    if args.edges is None:
        print("错误：需要 --edges", file=sys.stderr)
        return 2
    try:
        edges = parse_edges(args.edges)
        total, components, chosen = kruskal(edges)
    except GraphError as error:
        print("错误：%s" % error, file=sys.stderr)
        return 1
    print("total=%d" % total)
    print("components=%d" % components)
    print("edges=%s" % ",".join("%s-%s(%d)" % edge for edge in chosen))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
