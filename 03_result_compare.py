from importlib import import_module
from math import isfinite
from pathlib import Path

import pandas as pd


# ==================== 一、基础配置 ====================

# 获取项目 results 文件夹的绝对路径
RESULTS = Path(__file__).resolve().parents[1] / "results"

# 三种算法的结果文件及对应的边权重
# BFS 不需要权重，Dijkstra 分别使用耗时和里程作为权重
ALGORITHMS = {
    "bfs": ("bfs_results.csv", None),
    "dijkstra_time": ("dijkstra_time_results.csv", "duration_min"),
    "dijkstra_distance": ("dijkstra_distance_results.csv", "distance_km"),
}


# ==================== 二、读取并检查历史结果 ====================

def read_saved_results():
    """
    读取三种算法已经保存的计算结果。

    检查内容：
    1. 三种算法的 pair_id 是否唯一；
    2. 三种算法是否包含相同的 OD 编号；
    3. 每个 OD 编号对应的起点和终点是否一致。
    """

    # 读取三个算法的结果，并将 pair_id 设置为索引
    # verify_integrity=True 用于检查是否存在重复编号
    saved = {
        name: pd.read_csv(
            RESULTS / filename
        ).set_index("pair_id", verify_integrity=True)
        for name, (filename, _) in ALGORITHMS.items()
    }

    # 以 BFS 结果中的 OD 起点和终点作为对照
    endpoints = saved["bfs"][["src", "dst"]].sort_index()

    # 逐一检查另外两种算法的 OD 信息
    for name, frame in saved.items():

        current_endpoints = frame[["src", "dst"]].sort_index()

        if not endpoints.equals(current_endpoints):
            raise ValueError(
                f"{name}：OD 编号或起点、终点与 BFS 结果不一致"
            )

    return saved


# ==================== 三、筛选代表性 OD ====================

def select_cases(saved):
    """
    从 200 对 OD 中筛选具有代表性的案例。

    计划筛选四类案例：

    1. bfs_vs_time：
       BFS 与最短耗时路径不同。

    2. bfs_vs_distance：
       BFS 与最短里程路径不同。

    3. all_same：
       三种算法得到的路径完全一致。

    4. all_distinct：
       三种算法得到的路径两两不同。

    优先选择不同的 OD，避免同一个案例重复使用。
    """

    # 提取三种算法的机场路径
    paths = pd.DataFrame({
        name: frame["path"]
        for name, frame in saved.items()
    })

    # 检查每对 OD 是否在三种算法中均可达
    reachable = pd.DataFrame({
        name: frame["reachable"].eq(True)
        for name, frame in saved.items()
    })

    # 仅保留三种算法均可达且路径不为空的 OD
    paths = paths.loc[
        reachable.all(axis=1)
    ].dropna().sort_index()

    # 分别比较三种算法的路径是否一致
    bfs_time = paths.bfs.eq(paths.dijkstra_time)

    bfs_distance = paths.bfs.eq(paths.dijkstra_distance)

    time_distance = paths.dijkstra_time.eq(
        paths.dijkstra_distance
    )

    # 计算 BFS 相比最短耗时算法多花费的时间
    durations = (
        saved["bfs"]["total_duration"]
        - saved["dijkstra_time"]["total_duration"]
    )

    # 获取 BFS 路径的交通段数
    edge_count = saved["bfs"]["edge_count"]

    # 检查最短里程路径是否包含地面接驳
    uses_ground = (
        saved["dijkstra_distance"]["ground_edge_count"]
        .gt(0)
        .reindex(paths.index)
    )

    # 定义四类代表性案例的筛选条件
    # score 用于从候选 OD 中挑选更有代表性的案例
    categories = [

        # 第一类：BFS 与最短耗时路径不同
        # 优先选择最短耗时和最短里程路径相同的案例
        (
            "bfs_vs_time",
            ~bfs_time,
            time_distance,
            durations,
            False
        ),

        # 第二类：BFS 与最短里程路径不同
        # 优先选择 BFS 与最短耗时路径相同的案例
        (
            "bfs_vs_distance",
            ~bfs_distance,
            bfs_time,
            edge_count,
            False
        ),

        # 第三类：三种算法的路径完全相同
        (
            "all_same",
            bfs_time & bfs_distance & time_distance,
            None,
            edge_count,
            True
        ),

        # 第四类：三种算法的路径两两不同
        # 优先选择最短里程路径包含地面接驳的案例
        (
            "all_distinct",
            ~bfs_time & ~bfs_distance & ~time_distance,
            uses_ground,
            durations,
            False
        ),
    ]

    selected = {}

    print(
        f"历史 OD 数量：{len(saved['bfs'])} 对"
    )

    print(
        f"三种算法均可达且有路径的 OD：{len(paths)} 对"
    )

    # 依次筛选四类代表性 OD
    for label, mask, preferred, score, ascending in categories:

        # 获取符合当前类别条件的 OD 编号
        candidates = paths.index[mask]

        # 排除已经被其他类别选中的 OD
        available = candidates.difference(
            selected.values()
        ).sort_values()

        if available.empty:
            raise ValueError(
                f"{label}：没有可供选择的独立代表性 OD"
            )

        # 如果存在优先条件，则优先从符合条件的 OD 中选择
        if preferred is not None:

            illustrative = available.intersection(
                paths.index[preferred]
            )

            if not illustrative.empty:
                available = illustrative

        # 按照评分排序，稳定排序保证结果可复现
        # 如果评分相同，则优先选择 pair_id 较小的 OD
        pair_id = (
            score.loc[available]
            .sort_values(
                ascending=ascending,
                kind="stable"
            )
            .index[0]
        )

        selected[label] = pair_id

        print(
            f"{label}：候选 {len(candidates)} 对，"
            f"最终选择 OD {pair_id}"
        )

    return selected


# ==================== 四、重新计算代表性 OD 路径 ====================

def replay_case(builder, graph, saved, category, pair_id):
    """
    对选中的代表性 OD 重新运行三种路径算法。

    逐项检查：
    1. 路径是否能够正确连接起点和终点；
    2. 路径中的交通段数量是否正确；
    3. 重新计算的耗时、里程是否与历史结果一致；
    4. 每一段交通边是否与实际路径对应；
    5. 记录航空和地面接驳的具体信息。

    使用算法实际返回的边，避免并行航班导致交通信息丢失。
    """

    # 获取当前 OD 的起点和终点
    src, dst = saved["bfs"].loc[
        pair_id, ["src", "dst"]
    ]

    print(
        f"\n========== OD {pair_id}：{src} → {dst} =========="
    )

    # 依次运行 BFS、最短耗时 Dijkstra 和最短里程 Dijkstra
    for name, (_, weight) in ALGORITHMS.items():

        # BFS 不需要权重
        # Dijkstra 根据不同权重分别计算最短路径
        if weight is None:
            run = builder.bfs(graph, src, dst)
        else:
            run = builder.dijkstra(
                graph,
                src,
                dst,
                weight=weight
            )

        if run is None:
            raise ValueError(
                f"OD {pair_id}：{name} 重新计算后无法到达终点"
            )

        # 获取算法返回的机场路径和具体交通边
        path = run["path"]
        edges = run["edges"]

        path_text = " -> ".join(path)

        # 检查路径结构是否正确
        if (
            len(path) != len(edges) + 1
            or path[0] != src
            or path[-1] != dst
        ):
            raise ValueError(
                f"OD {pair_id}：{name} 返回的路径结构不正确"
            )

        # 统计路径总耗时
        duration = sum(
            edge["duration_min"]
            for edge in edges
        )

        # 统计路径总里程
        distance = sum(
            edge["distance_km"]
            for edge in edges
        )

        # 统计航空交通段数
        flight_count = sum(
            edge["mode"] == "flight"
            for edge in edges
        )

        # 汇总路径指标
        totals = {
            "edge_count": len(edges),
            "total_duration": duration,
            "total_distance_km": distance,
            "flight_edge_count": flight_count,
            "ground_edge_count": len(edges) - flight_count,
        }

        # 获取对应算法的历史结果
        historical = saved[name].loc[pair_id]

        # 准备需要核对的指标
        compared = {
            "path": path_text,
            **totals
        }

        # 历史里程结果保存到小数点后两位
        compared["total_distance_km"] = round(
            distance, 2
        )

        # 仅核对历史 CSV 中实际存在的字段
        verified = [
            field
            for field in compared
            if field in historical.index
        ]

        # 逐项比较重新计算的结果与历史结果
        for field in verified:

            if compared[field] != historical[field]:
                raise ValueError(
                    f"OD {pair_id}，{name}，指标 {field} 不一致："
                    f"重新计算值 {compared[field]!r}，"
                    f"历史值 {historical[field]!r}"
                )

        # 输出当前算法的整体路径信息
        print(
            f"\n算法：{name}"
        )

        print(
            f"路径：{path_text}"
        )

        print(
            f"交通段数：{len(edges)}"
        )

        print(
            f"航空段数：{flight_count}"
        )

        print(
            f"地面接驳段数：{len(edges) - flight_count}"
        )

        print(
            f"总耗时：{duration} 分钟"
        )

        print(
            f"总里程：{distance:.2f} km"
        )

        print(
            "历史 CSV 核对通过："
            + ", ".join(verified)
        )

        # 逐段输出具体交通信息
        for number, (
            edge_src,
            edge_dst,
            edge
        ) in enumerate(
            zip(path, path[1:], edges),
            1
        ):

            # 检查当前交通边是否与路径顺序一致
            if edge["dst"] != edge_dst:
                raise ValueError(
                    f"OD {pair_id}：第 {number} 段交通边与路径不匹配"
                )

            # 区分里程的数据来源
            # 航空边采用原始航线表中的距离
            # 地面边采用 Haversine 大圆距离代理值
            if edge["mode"] == "flight":
                basis = "route_csv"
            else:
                basis = "ground_haversine_proxy"

            print(
                f"  第 {number} 段："
                f"{edge_src} → {edge_dst} | "
                f"方式：{edge['mode']} | "
                f"航空公司：{edge['airline'] or '无'} | "
                f"经停：{edge['stops']} | "
                f"耗时：{edge['duration_min']} 分钟 | "
                f"里程：{edge['distance_km']:.2f} km | "
                f"里程来源：{basis}"
            )

            # 生成逐段交通记录，供后续保存为 CSV
            yield {
                "case_category": category,
                "pair_id": pair_id,
                "od_src": src,
                "od_dst": dst,
                "algorithm": name,
                "path": path_text,
                "segment_no": number,
                "src": edge_src,
                "dst": edge_dst,
                "mode": edge["mode"],
                "airline": edge["airline"],
                "stops": edge["stops"],
                "duration_min": edge["duration_min"],
                "distance_km": edge["distance_km"],
                "distance_basis": basis,
                "includes_haversine_proxy": totals["ground_edge_count"] > 0,
                **totals,
            }


# ==================== 五、主程序 ====================

def main():

    print("\n========== 第一步：加载图构建程序 ==========")

    # 动态导入 02_graph_builder.py
    # 导入时不会执行其中仅在主程序下运行的批量计算任务
    builder = import_module("02_graph_builder")

    # 读取机场、航空航线和地面接驳数据
    airports, routes, ground = builder.load_graph_inputs()

    print("机场数据加载完成")
    print(f"机场数量：{len(airports)}")
    print(f"航空航线数量：{len(routes)}")
    print(f"地面接驳数量：{len(ground)}")

    print("\n========== 第二步：检查地面接驳机场坐标 ==========")

    # 获取所有地面接驳涉及的机场 ID
    ground_ids = set(ground.src) | set(ground.dst)

    # 根据机场 ID 获取对应的经纬度
    coordinates = (
        airports
        .set_index("airport_id", verify_integrity=True)
        .reindex(list(ground_ids))
    )

    # 检查经纬度是否缺失或超出合法范围
    valid_coordinates = (
        coordinates.lat.between(-90, 90)
        & coordinates.lon.between(-180, 180)
    )

    if not valid_coordinates.all():
        raise ValueError(
            "地面接驳端点存在缺失或无效的经纬度"
        )

    print(
        f"地面接驳端点数量：{len(ground_ids)}"
    )

    print("所有地面接驳端点的经纬度检查通过")

    print("\n========== 第三步：重新构建交通网络 ==========")

    # 使用与原算法相同的构图函数
    graph = builder.build_graph(
        airports,
        routes,
        ground
    )

    # 统计图中的节点数和边数
    edge_total = sum(
        len(edges)
        for edges in graph.values()
    )

    # 检查图结构是否与之前实验一致
    if (len(graph), edge_total) != (612, 5221):
        raise ValueError(
            f"图结构异常：当前节点 {len(graph)} 个，"
            f"边 {edge_total} 条"
        )

    # 检查所有边的耗时和里程是否有效
    for src, edges in graph.items():

        for edge in edges:

            for field in (
                "duration_min",
                "distance_km"
            ):

                value = edge[field]

                if (
                    value is None
                    or not isfinite(value)
                    or value < 0
                ):
                    raise ValueError(
                        f"{src} → {edge['dst']}："
                        f"边权重 {field} 无效，当前值为 {value}"
                    )

    print(f"图节点数量：{len(graph)}")
    print(f"图边数量：{edge_total}")

    print(
        "里程计算口径："
        "航空原始里程 + 地面 Haversine 大圆代理里程"
    )

    print("\n========== 第四步：读取历史算法结果 ==========")

    # 读取三种算法的历史计算结果
    saved = read_saved_results()

    print("三种算法的 OD 编号及起终点检查通过")

    print("\n========== 第五步：筛选代表性 OD ==========")

    # 从 200 对 OD 中筛选四类代表性案例
    selected = select_cases(saved)

    print("\n代表性 OD 筛选完成")

    print("\n========== 第六步：重新运行三种算法并核验 ==========")

    # 对四类代表性 OD 逐一运行三种算法
    # 同时记录每一段交通的详细信息
    rows = [
        segment
        for category, pair_id in selected.items()
        for segment in replay_case(
            builder,
            graph,
            saved,
            category,
            pair_id
        )
    ]

    print("\n所有代表性 OD 的路径复现与历史结果核对通过")

    print("\n========== 第七步：保存代表性 OD 逐段明细 ==========")

    # 将逐段交通信息保存为 CSV
    # 不覆盖原有的算法结果文件和对比结果文件
    output = RESULTS / "representative_od_details.csv"

    pd.DataFrame(rows).to_csv(
        output,
        index=False,
        encoding="utf-8-sig"
    )

    print(f"代表性 OD 数量：{len(selected)}")

    print(f"逐段交通记录数量：{len(rows)}")

    print(f"文件保存位置：{output}")

    print("\n========== 全部任务完成 ==========")


if __name__ == "__main__":
    main()
