"""最小生成森林：并查集 + 稳定排序的 Kruskal。只用标准库。"""


class GraphError(Exception):
    """输入不合法，message 会指出是第几条边（从 1 开始）。"""

    def __init__(self, message):
        super().__init__(message)
        self.message = message


def parse_edges(text):
    """解析 "a-b:1,c-d:2" 为 [(left, right, weight), ...]。

    权重必须是非负十进制整数；缺 "-"、缺 ":"、权重非法都报 GraphError，
    并指出是第几条边（下标从 1 开始，空项也占位计数）。
    """
    edges = []
    for index, item in enumerate(text.split(","), start=1):
        item = item.strip()
        if not item:
            continue
        pair, colon, raw_weight = item.partition(":")
        left, dash, right = pair.partition("-")
        if not colon or not dash:
            raise GraphError("第 %d 条边格式不对（应为 u-v:权重）：%s" % (index, item))
        raw_weight = raw_weight.strip()
        if not raw_weight or not raw_weight.isdigit():
            raise GraphError("第 %d 条边权重必须是非负十进制整数：%s" % (index, item))
        left, right = left.strip(), right.strip()
        if not left or not right:
            raise GraphError("第 %d 条边缺少顶点名：%s" % (index, item))
        edges.append((left, right, int(raw_weight)))
    return edges


def nodes_of(edges):
    """按第一次出现的顺序收集顶点。"""
    seen = set()
    nodes = []
    for left, right, _ in edges:
        for node in (left, right):
            if node not in seen:
                seen.add(node)
                nodes.append(node)
    return nodes


class UnionFind:
    """并查集：find 顺父指针走到根并做路径压缩，union 按大小合并。"""

    def __init__(self, nodes):
        self.parent = {node: node for node in nodes}
        self.size = {node: 1 for node in nodes}

    def find(self, node):
        root = node
        while self.parent[root] != root:
            root = self.parent[root]
        while self.parent[node] != node:
            parent = self.parent[node]
            self.parent[node] = root
            node = parent
        return root

    def union(self, left, right):
        root_left = self.find(left)
        root_right = self.find(right)
        if root_left == root_right:
            return False
        if self.size[root_left] < self.size[root_right]:
            root_left, root_right = root_right, root_left
        self.parent[root_right] = root_left
        self.size[root_left] += self.size[root_right]
        return True


def kruskal(edges):
    """返回 (总权重, 连通分量数, 选中的边)。

    边按权重升序、权重相同时按输入顺序稳定选取；自环忽略，
    平行边天然只取权重最小的一条。
    """
    nodes = nodes_of(edges)
    forest = UnionFind(nodes)
    chosen = []
    total = 0
    ordered = sorted(enumerate(edges), key=lambda item: (item[1][2], item[0]))
    for _index, (left, right, weight) in ordered:
        if left == right:
            continue
        if forest.union(left, right):
            chosen.append((left, right, weight))
            total += weight
    components = len(nodes) - len(chosen)
    return total, components, chosen
