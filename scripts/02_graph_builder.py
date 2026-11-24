import pandas as pd
from collections import deque
import heapq
import math
from numbers import Real
from pathlib import Path


def _finite_number(value):
    return isinstance(value, Real) and not isinstance(value, bool) and math.isfinite(value)


def _checked_coordinates(airport_id, airport_coords):
    if airport_id not in airport_coords:
        raise ValueError(f"机场 {airport_id!r} 缺少 lat/lon 坐标")
    try:
        lat, lon = airport_coords[airport_id]
    except (TypeError, ValueError) as exc:
        raise ValueError(f"机场 {airport_id!r} 的 lat/lon 坐标格式无效") from exc
    for field, value, limit in (("lat", lat, 90), ("lon", lon, 180)):
        if not _finite_number(value) or not -limit <= value <= limit:
            raise ValueError(f"机场 {airport_id!r} 的 {field}={value!r} 无效，"
                             f"须为 [-{limit}, {limit}] 内的有限数值")
    return lat, lon


def haversine_distance(src, dst, airport_coords):

    lat1, lon1 = _checked_coordinates(src, airport_coords)
    lat2, lon2 = _checked_coordinates(dst, airport_coords)

    # 经纬度转换为弧度
    lat1 = math.radians(lat1)
    lon1 = math.radians(lon1)

    lat2 = math.radians(lat2)
    lon2 = math.radians(lon2)

    dlat = lat2 - lat1
    dlon = lon2 - lon1

    # Haversine公式
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(lat1)
        * math.cos(lat2)
        * math.sin(dlon / 2) ** 2
    )

    # 避免浮点误差
    a = max(0, min(1, a))

    # 地球平均半径，单位km
    R = 6371

    distance = 2 * R * math.asin(math.sqrt(a))

    return distance


def _valid_airport_id(value):
    return isinstance(value, str) and bool(value.strip())


def _check_weight(value, field, record, *, allow_zero=False):
    if not _finite_number(value) or value < 0 or (value == 0 and not allow_zero):
        expected = "有限非负数" if allow_zero else "有限正数"
        raise ValueError(f"{record} 的 {field}={value!r} 无效，须为{expected}")


def _check_endpoints(row, record, known_ids, graph):
    for field in ("src", "dst"):
        airport_id = row[field]
        if not _valid_airport_id(airport_id) or airport_id not in known_ids:
            raise ValueError(f"{record} 的 {field}={airport_id!r} 不存在于机场表")
        if airport_id not in graph:
            raise ValueError(f"{record} 的 {field}={airport_id!r} 不属于开放机场图节点")


def build_graph(airports, routes, ground, *, verbose=False):
    """Build the directed graph in CSV order to preserve algorithm tie-breaking."""
    airport_ids = airports["airport_id"]
    invalid = ~airport_ids.map(_valid_airport_id) | airport_ids.duplicated(keep=False)
    if invalid.any():
        records = airport_ids.loc[invalid].to_string()
        raise ValueError(f"airport_id 为空、非法或重复（索引及机场 ID）\n{records}")
    known_ids = set(airport_ids)

    # 筛选正常运营的机场
    active_airports = airports[
        airports["active"] == 1
    ].copy()

    # 初始化空字典
    graph = {}

    # 将所有正常运营机场加入图中
    for airport_id in active_airports["airport_id"]:
        graph[airport_id] = []

    if verbose:
        print("图的节点数量：", len(graph))
        print("\n前5个节点：")
        print(list(graph.items())[:5])

    # 遍历每条清洗后的飞机航线
    for index, row in routes.iterrows():

        src = row["src"]
        dst = row["dst"]

        record = f"航空边（索引 {index!r}，{src!r} → {dst!r}）"
        _check_endpoints(row, record, known_ids, graph)
        _check_weight(row["duration_min"], "duration_min", record)
        _check_weight(row["distance_km"], "distance_km", record)
        edge = {
            "dst": dst,
            "mode": "flight",
            "airline": row["airline"],
            "duration_min": row["duration_min"],
            "distance_km": row["distance_km"],
            "stops": row["stops"],
            "codeshare": row["codeshare"]
        }

        graph[src].append(edge)

    if verbose:
        print("\n飞机航线添加完成")
        print("飞机航线边数：", sum(len(edges) for edges in graph.values()))


    # 建立机场经纬度字典

    airport_coords = {}

    for _, row in airports.iterrows():

        airport_coords[row["airport_id"]] = (
            row["lat"],
            row["lon"]
        )

    for index, row in ground.iterrows():

        src = row["src"]
        dst = row["dst"]

        record = f"地面边（索引 {index!r}，{src!r} → {dst!r}）"
        _check_endpoints(row, record, known_ids, graph)
        _check_weight(row["duration_min"], "duration_min", record)
        try:
            distance = haversine_distance(src, dst, airport_coords)
        except ValueError as exc:
            raise ValueError(f"{record} 坐标无效：{exc}") from exc
        _check_weight(distance, "distance_km", record, allow_zero=True)
        edge = {
            "dst": dst,
            "mode": row["mode"],
            "airline": None,
            "duration_min": row["duration_min"],
            "distance_km": distance,
            "stops": row["stops"],
            "codeshare": None
        }

        graph[src].append(edge)

    if verbose:
        print("\n地面接驳添加完成")
    return graph


def validate_od(od, graph):
    """Reject invalid OD records before the first algorithm or output write."""
    errors = []
    duplicates = od["pair_id"].duplicated(keep=False).to_numpy()
    for (index, row), duplicate in zip(od.iterrows(), duplicates):
        pair_id = row["pair_id"]
        reasons = []
        if pd.isna(pair_id) or (isinstance(pair_id, str) and not pair_id.strip()):
            reasons.append("pair_id 为空")
        if duplicate:
            reasons.append("pair_id 重复")
        for field in ("src", "dst"):
            airport_id = row[field]
            if not _valid_airport_id(airport_id) or airport_id not in graph:
                reasons.append(f"{field}={airport_id!r} 不是有效图节点")
        if reasons:
            errors.append(f"索引 {index!r}，pair_id={pair_id!r}，"
                          f"src={row['src']!r}，dst={row['dst']!r}：{'，'.join(reasons)}")
    if errors:
        raise ValueError("OD 输入无效\n" + "\n".join(errors))


def load_graph_inputs():
    # Resolve input files from the project regardless of the caller's directory.
    data = Path(__file__).resolve().parents[1] / "data"
    return (
        pd.read_csv(data / "raw" / "Q02_airports.csv"),
        pd.read_csv(data / "processed" / "routes_clean.csv"),
        pd.read_csv(data / "processed" / "ground_links_clean.csv"),
    )


def bfs(graph, start, end):
    """
    使用广度优先搜索寻找最少边数路径。

    graph：邻接表
    start：起点机场
    end：终点机场
    """

    # 1. 初始化队列
    queue = deque([start])

    # 2. 记录访问过的节点
    visited = {start}

    # 3. 记录每个节点是从哪里到达的
    parent = {start: None}

    # 4. 记录到达节点时使用的具体边
    parent_edge = {}

    # 5. 开始搜索
    while queue:

        # 取出队首机场
        current = queue.popleft()

        # 如果已经到达终点，停止搜索
        if current == end:
            break

        # 遍历当前机场的所有出边
        for edge in graph[current]:

            next_airport = edge["dst"]

            # 如果没有访问过
            if next_airport not in visited:

                # 标记访问
                visited.add(next_airport)

                # 记录前驱节点
                parent[next_airport] = current

                # 记录使用的具体交通边
                parent_edge[next_airport] = edge

                # 加入队列
                queue.append(next_airport)

    # 6. 如果终点没有被访问，说明不可达
    if end not in visited:
        return None

    # 7. 从终点反向恢复路径
    path = []
    path_edges = []

    current = end

    while current is not None:

        path.append(current)

        if current != start:
            path_edges.append(parent_edge[current])

        current = parent[current]

    # 8. 反转路径
    path.reverse()
    path_edges.reverse()

    return {
        "path": path,
        "edges": path_edges,
        "edge_count": len(path_edges),
        "transfer_count": max(0, len(path_edges) - 1)
    }


def dijkstra(graph, start, end, weight="duration_min"):
    """
    Dijkstra 最短路径算法

    weight:
        duration_min：最短总耗时
        distance_km：最短总里程
    """

    # 1. 初始化距离字典
    dist = {node: float("inf") for node in graph}

    # 起点到自己的距离为0
    dist[start] = 0

    # 2. 初始化前驱节点
    parent = {start: None}
    parent_edge = {}

    # 3. 初始化优先队列
    pq = [(0, start)]

    # 4. 开始搜索
    while pq:

        current_dist, current = heapq.heappop(pq)

        # 跳过已经过期的队列记录
        if current_dist > dist[current]:
            continue

        # 找到终点
        if current == end:
            break

        # 5. 遍历当前机场的所有出边
        for edge in graph[current]:

            next_airport = edge["dst"]

            # 获取边权重
            edge_weight = edge[weight]

            # 距离字段为空时不能参与计算
            if edge_weight is None:
                continue

            # 计算新的累计距离
            new_dist = current_dist + edge_weight

            # 6. 松弛操作
            if new_dist < dist[next_airport]:

                dist[next_airport] = new_dist

                parent[next_airport] = current
                parent_edge[next_airport] = edge

                # 加入优先队列
                heapq.heappush(
                    pq,
                    (new_dist, next_airport)
                )

    # 7. 判断终点是否可达
    if dist[end] == float("inf"):
        return None

    # 8. 恢复路径
    path = []
    path_edges = []

    current = end

    while current is not None:

        path.append(current)

        if current != start:
            path_edges.append(parent_edge[current])

        current = parent[current]

    path.reverse()
    path_edges.reverse()

    return {
        "path": path,
        "edges": path_edges,
        "total_weight": dist[end],
        "edge_count": len(path_edges)
    }



def main():
    airports, routes, ground = load_graph_inputs()
    od = pd.read_csv("../data/raw/Q02_od_pairs.csv")
    print("OD数量：", len(od))
    graph = build_graph(airports, routes, ground, verbose=True)
    validate_od(od, graph)
    airport_coords = dict(zip(airports["airport_id"], zip(airports["lat"], airports["lon"])))

    print("\n========== 地面接驳距离检查 ==========")

    for _, row in ground.iterrows():

        src = row["src"]
        dst = row["dst"]

        distance = haversine_distance(src, dst, airport_coords)

        print(
            src,
            "->",
            dst,
            "交通方式：",
            row["mode"],
            "地理距离：",
            round(distance, 2),
            "km"
        )

    print("最终图节点数：", len(graph))

    print("最终图边数：",
          sum(len(edges) for edges in graph.values()))

    print("\n========== 图结构检查 ==========")

    # 查看A0000机场的所有出边
    print("\nA0000机场的邻接边：")

    for edge in graph["A0000"]:
        print(edge)

    # 检查孤立机场
    print("\nA0592机场的邻接边：")
    print(graph["A0592"])

    # 检查图的规模是否正确
    assert len(graph) == 612

    assert sum(
        len(edges) for edges in graph.values()
    ) == 5221

    print("\n图结构数量检查通过")


    # 1. 检查地面接驳的具体数据

    print("\n========== 地面接驳详细信息 ==========")

    print(ground.to_string(index=False))

    print("\n========== 地面接驳 stops 分布 ==========")

    print(ground["stops"].value_counts().sort_index())

    print("\n========== 地面接驳交通方式 ==========")

    print(ground["mode"].value_counts())

    print("\n========== 地面接驳耗时统计 ==========")

    print(ground["duration_min"].describe())

    # 选择一对OD进行测试
    test_start = od.iloc[0]["src"]
    test_end = od.iloc[0]["dst"]

    result = bfs(graph, test_start, test_end)

    print("\n========== BFS单条路径测试 ==========")

    print("起点：", test_start)
    print("终点：", test_end)

    if result is None:
        print("不存在可达路径")

    else:
        print("路径：", " -> ".join(result["path"]))
        print("交通段数：", result["edge_count"])
        print("换乘次数（按交通段数减一）：",
              result["transfer_count"])

        print("\n逐段交通信息：")

        for i, edge in enumerate(result["edges"], 1):
            print(
                i,
                edge["mode"],
                "->",
                edge["dst"],
                "耗时：",
                edge["duration_min"],
                "分钟"
            )


    # =====================================
    # BFS 批量计算 200 对 OD
    # =====================================

    results = []

    for _, row in od.iterrows():

        pair_id = row["pair_id"]
        start = row["src"]
        end = row["dst"]

        result = bfs(graph, start, end)

        if result is None:

            results.append({
                "pair_id": pair_id,
                "src": start,
                "dst": end,
                "reachable": False,
                "path": None,
                "edge_count": None,
                "transfer_count": None,
                "total_duration": None
            })

        else:

            total_duration = sum(
                edge["duration_min"]
                for edge in result["edges"]
            )

            results.append({
                "pair_id": pair_id,
                "src": start,
                "dst": end,
                "reachable": True,
                "path": " -> ".join(result["path"]),
                "edge_count": result["edge_count"],
                "transfer_count": result["transfer_count"],
                "total_duration": total_duration
            })

    # 转换成 DataFrame
    bfs_results = pd.DataFrame(results)

    # 保存结果
    bfs_results.to_csv(
        "../results/bfs_results.csv",
        index=False,
        encoding="utf-8-sig"
    )

    print("\n========== BFS批量计算结果 ==========")

    print("OD总数：", len(bfs_results))

    print("可达数量：",
          bfs_results["reachable"].sum())

    print("不可达数量：",
          (~bfs_results["reachable"]).sum())

    print("\n交通段数统计：")

    print(
        bfs_results["edge_count"].describe()
    )

    print("\n总耗时统计：")

    print(
        bfs_results["total_duration"].describe()
    )

    print("\n前10条结果：")

    print(bfs_results.head(10).to_string(index=False))

    print("\n========== Dijkstra最短耗时测试 ==========")

    test_start = od.iloc[0]["src"]
    test_end = od.iloc[0]["dst"]

    result = dijkstra(
        graph,
        test_start,
        test_end,
        weight="duration_min"
    )

    if result is None:

        print("不存在可达路径")

    else:

        print("起点：", test_start)
        print("终点：", test_end)

        print("路径：", " -> ".join(result["path"]))

        print("交通段数：", result["edge_count"])

        print("总耗时：", result["total_weight"], "分钟")

        print("\n逐段信息：")

        for i, edge in enumerate(result["edges"], 1):

            print(
                i,
                edge["mode"],
                "->",
                edge["dst"],
                edge["duration_min"],
                "分钟"
            )


    # ==========================================
    # Dijkstra：200对OD最短总耗时批量计算
    # ==========================================

    dijkstra_time_results = []

    for _, row in od.iterrows():

        pair_id = row["pair_id"]
        start = row["src"]
        end = row["dst"]

        result = dijkstra(
            graph,
            start,
            end,
            weight="duration_min"
        )

        if result is None:

            dijkstra_time_results.append({
                "pair_id": pair_id,
                "src": start,
                "dst": end,
                "reachable": False,
                "path": None,
                "edge_count": None,
                "total_duration": None
            })

        else:

            dijkstra_time_results.append({
                "pair_id": pair_id,
                "src": start,
                "dst": end,
                "reachable": True,
                "path": " -> ".join(result["path"]),
                "edge_count": result["edge_count"],
                "total_duration": result["total_weight"]
            })


    # 转换为DataFrame
    dijkstra_time_df = pd.DataFrame(
        dijkstra_time_results
    )

    # 保存结果
    dijkstra_time_df.to_csv(
        "../results/dijkstra_time_results.csv",
        index=False,
        encoding="utf-8-sig"
    )


    # 输出统计
    print("\n========== Dijkstra最短耗时批量结果 ==========")

    print("OD总数：", len(dijkstra_time_df))

    print(
        "可达数量：",
        dijkstra_time_df["reachable"].sum()
    )

    print(
        "不可达数量：",
        (~dijkstra_time_df["reachable"]).sum()
    )

    print("\n交通段数统计：")

    print(
        dijkstra_time_df["edge_count"].describe()
    )

    print("\n最短总耗时统计：")

    print(
        dijkstra_time_df["total_duration"].describe()
    )

    print("\n前10条结果：")

    print(
        dijkstra_time_df.head(10).to_string(index=False)
    )


    # ==========================================
    # Dijkstra：最短总里程单条测试
    # ==========================================

    test_start = od.iloc[0]["src"]
    test_end = od.iloc[0]["dst"]

    result = dijkstra(
        graph,
        test_start,
        test_end,
        weight="distance_km"
    )

    print("\n========== Dijkstra最短总里程测试 ==========")

    print("起点：", test_start)
    print("终点：", test_end)

    if result is None:

        print("不存在可达路径")

    else:

        print("路径：", " -> ".join(result["path"]))

        print("交通段数：", result["edge_count"])

        total_distance = sum(
            edge["distance_km"]
            for edge in result["edges"]
        )

        print("总里程：", round(total_distance, 2), "km")

        print("\n逐段信息：")

        for i, edge in enumerate(result["edges"], 1):

            print(
                i,
                edge["mode"],
                "->",
                edge["dst"],
                "距离：",
                round(edge["distance_km"], 2),
                "km"
            )


    # ==========================================
    # Dijkstra：最短总里程批量计算
    # ==========================================

    import os

    distance_results = []

    for _, row in od.iterrows():

        pair_id = row["pair_id"]
        src = row["src"]
        dst = row["dst"]

        result = dijkstra(
            graph,
            src,
            dst,
            weight="distance_km"
        )

        if result is None:

            distance_results.append({
                "pair_id": pair_id,
                "src": src,
                "dst": dst,
                "reachable": False,
                "path": None,
                "edge_count": None,
                "total_distance_km": None,
                "flight_edge_count": None,
                "ground_edge_count": None
            })

            continue

        edges = result["edges"]

        # 计算总距离
        total_distance = sum(
            edge["distance_km"] for edge in edges
        )

        # 统计飞机边和地面接驳边
        flight_count = sum(
            edge["mode"] == "flight" for edge in edges
        )

        ground_count = len(edges) - flight_count

        distance_results.append({

            "pair_id": pair_id,
            "src": src,
            "dst": dst,

            "reachable": True,

            "path": " -> ".join(result["path"]),

            "edge_count": len(edges),

            "total_distance_km": round(
                total_distance, 2
            ),

            "flight_edge_count": flight_count,

            "ground_edge_count": ground_count
        })


    # 转换为DataFrame
    distance_df = pd.DataFrame(distance_results)


    # 保存结果
    os.makedirs("../results", exist_ok=True)

    distance_df.to_csv(
        "../results/dijkstra_distance_results.csv",
        index=False,
        encoding="utf-8-sig"
    )


    # ==========================================
    # 统计结果
    # ==========================================

    print("\n========== Dijkstra最短总里程批量结果 ==========")

    print("OD总数：", len(distance_df))

    print(
        "可达数量：",
        distance_df["reachable"].sum()
    )

    print(
        "不可达数量：",
        (~distance_df["reachable"]).sum()
    )

    reachable_df = distance_df[
        distance_df["reachable"]
    ]

    print("\n交通段数统计：")

    print(reachable_df["edge_count"].describe())

    print("\n最短总里程统计：")

    print(
        reachable_df["total_distance_km"].describe()
    )

    print("\n前10条结果：")

    print(distance_df.head(10).to_string(index=False))

    print("\n结果已保存：")

    print("../results/dijkstra_distance_results.csv")


if __name__ == "__main__":
    main()
