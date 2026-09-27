# mst-kruskal

Kruskal 最小生成森林（并查集 + 稳定排序），只用 Python 标准库。

```
python3 -m mstk.cli --edges 'a-b:1,b-c:1,a-c:1'
python3 -m mstk.cli --edges 'a-b:1,c-d:2'
python3 -m unittest discover -s tests -v
```

## 口径（README 为准）

- **环检测要用完整的并查集**：find 必须顺着父指针走到根（带路径压缩），union 按秩或大小合并。
  `--edges 'a-b:1,b-c:1,a-c:1'` 按口径是 `total=2`、`components=1`、`edges=a-b(1),b-c(1)`，
  现在并查集只看一层父指针，环没被认出来，给 `total=3`。
- **连通分量数**：`components=` 是分量个数，等于顶点数减去选中的边数。同一个三角形因为多塞了一条环边，
  现在给 `components=0`（应 1）。
- **稳定排序**：边按权重升序取，权重相同时按输入顺序取，同一输入结果确定。
- 自环忽略；平行边保留权重最小的那条；空输入给 `total=0`、`components=0`、`edges=`（空）。
- 输入：`--edges` 是逗号分隔的 `u-v:权重`；权重必须是非负十进制整数，负数、非数字、缺 `-`、缺 `:`
  都要报错并指出是第几条边。
- 不变量：选中的边不能成环；`total` 等于选中边权重之和；`components` 等于顶点数减去选中边数；
  同一输入重复运行结果相同。
- 规模：5 万个顶点、20 万条边要在 3 秒内算完；不许每加一条边就 DFS/BFS 查一次环。
- 对照自证：顶点数 ≤ 8、边数 ≤ 12 的随机小图，与「枚举所有边子集取最小合法森林」的穷举逐例一致。

## 实现要点

- `UnionFind.find` 顺父指针走到根并做路径压缩，`union` 按秩合并，环检测准确。
- 分量数 = 顶点数 - 选中边数；三角形 `total=2`、`components=1`。
- 权重校验为非负十进制整数，非法输入报错并指出第几条边。

## 计划新增的能力

```
--edges 边表    逗号分隔的 u-v:权重
```

## 输出

```
total=2
components=1
edges=a-b(1),b-c(1)
```

## 目录

```
mstk/mst.py     解析、并查集与 Kruskal
mstk/cli.py     命令行入口
tests/          unittest 用例
```
