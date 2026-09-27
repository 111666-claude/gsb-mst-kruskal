"""最小生成森林。只用标准库。并查集（路径压缩 + 按秩合并）+ 稳定排序的 Kruskal。"""

import re

_WEIGHT_RE = re.compile(r"[0-9]+")


class GraphError(Exception):
    """输入不合法，消息里带第几条边（从 1 开始数）。"""

    def __init__(self, message):
        super().__init__(message)
        self.message = message


def parse_edges(text):
    """解析 "a-b:1,c-d:2"。权重必须是非负十进制整数，出错报第几条边。"""
    edges = []
    for index, item in enumerate(text.split(","), start=1):
        item = item.strip()
        if not item:
            continue
        pair, sep, raw_weight = item.partition(":")
        if not sep:
            raise GraphError("第 %d 条边缺少 ':'：%s" % (index, item))
        left, dash, right = pair.partition("-")
        if not dash:
            raise GraphError("第 %d 条边缺少 '-'：%s" % (index, item))
        left, right, raw_weight = left.strip(), right.strip(), raw_weight.strip()
        if not left or not right:
            raise GraphError("第 %d 条边顶点为空：%s" % (index, item))
        if not _WEIGHT_RE.fullmatch(raw_weight):
            raise GraphError(
                "第 %d 条边权重必须是非负十进制整数：%s" % (index, item)
            )
        edges.append((left, right, int(raw_weight)))
    return edges


def nodes_of(edges):
    """按第一次出现的顺序收集顶点。"""
    seen = []
    known = set()
    for left, right, _ in edges:
        for node in (left, right):
            if node not in known:
                known.add(node)
                seen.append(node)
    return seen


class UnionFind:
    """并查集：find 顺父指针走到根并做路径压缩，union 按秩合并。"""

    def __init__(self, nodes):
        self.parent = {node: node for node in nodes}
        self.rank = {node: 0 for node in nodes}

    def find(self, node):
        parent = self.parent
        root = node
        while parent[root] != root:
            root = parent[root]
        # 路径压缩：沿途节点直接挂到根上
        while parent[node] != root:
            parent[node], node = root, parent[node]
        return root

    def union(self, left, right):
        root_left, root_right = self.find(left), self.find(right)
        if root_left == root_right:
            return False
        if self.rank[root_left] < self.rank[root_right]:
            root_left, root_right = root_right, root_left
        self.parent[root_right] = root_left
        if self.rank[root_left] == self.rank[root_right]:
            self.rank[root_left] += 1
        return True


def kruskal(edges):
    """返回 (总权重, 连通分量数, 选中的边)。

    边按权重升序取，权重相同按输入顺序（sorted 稳定）；自环忽略；
    平行边只留权重最小的那条（其余成环被跳过）。
    """
    nodes = nodes_of(edges)
    forest = UnionFind(nodes)
    chosen = []
    total = 0
    for left, right, weight in sorted(edges, key=lambda edge: edge[2]):
        if left == right:
            continue
        if not forest.union(left, right):
            continue
        chosen.append((left, right, weight))
        total += weight
    components = len(nodes) - len(chosen)
    _check_invariants(nodes, chosen, total, components)
    return total, components, chosen


def _check_invariants(nodes, chosen, total, components):
    """复核：选中的边不成环；total 是权重之和；components = 顶点数 - 边数。"""
    assert total == sum(weight for _, _, weight in chosen)
    assert components == len(nodes) - len(chosen)
    forest = UnionFind(nodes)
    for left, right, _ in chosen:
        assert forest.union(left, right), "选中的边成环：%s-%s" % (left, right)
