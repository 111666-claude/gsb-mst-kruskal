"""最小生成森林。只用标准库。缺陷：并查集不顺着父指针走，环检测失效。"""


class GraphError(Exception):
    """输入不合法。缺陷：不带边下标。"""

    def __init__(self, message):
        super().__init__(message)
        self.message = message


def parse_edges(text):
    """解析 "a-b:1,c-d:2"。缺陷：不校验权重，出错不给下标。"""
    edges = []
    for item in text.split(","):
        item = item.strip()
        if not item:
            continue
        pair, sep, raw_weight = item.partition(":")
        left, dash, right = pair.partition("-")
        if not sep or not dash:
            raise GraphError("边格式不对：%s" % item)
        edges.append((left.strip(), right.strip(), int(raw_weight)))
    return edges


def nodes_of(edges):
    """按第一次出现的顺序收集顶点。"""
    seen = []
    for left, right, _ in edges:
        for node in (left, right):
            if node not in seen:
                seen.append(node)
    return seen


class UnionFind:
    """并查集。缺陷：find 只看一层，union 也不合并整棵树。"""

    def __init__(self, nodes):
        self.parent = {node: node for node in nodes}

    def find(self, node):
        # 缺陷：没有顺着父指针往上找，也没做路径压缩
        return self.parent[node]

    def union(self, left, right):
        self.parent[left] = right


def kruskal(edges):
    """返回 (总权重, 连通分量数, 选中的边)。缺陷：环检测失效。"""
    nodes = nodes_of(edges)
    forest = UnionFind(nodes)
    chosen = []
    total = 0
    for left, right, weight in sorted(edges, key=lambda edge: edge[2]):
        if left == right:
            continue
        if forest.find(left) == forest.find(right):
            continue
        forest.union(left, right)
        chosen.append((left, right, weight))
        total += weight
    # 缺陷：分量数直接按「顶点数 - 选中边数」算，多加进来的环边会把它算少
    components = len(nodes) - len(chosen)
    return total, components, chosen
