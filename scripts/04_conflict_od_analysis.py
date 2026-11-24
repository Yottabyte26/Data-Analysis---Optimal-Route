from pathlib import Path

import pandas as pd


# ==================== 一、基础配置 ====================

# 获取项目 results 文件夹的绝对路径
RESULTS = Path(__file__).resolve().parents[1] / "results"

# 本次实验的 OD 总数量
EXPECTED_OD_COUNT = 200

# OD 匹配时使用的关键字段
KEY = ["pair_id", "src", "dst"]


# ==================== 二、读取并检查算法结果 ====================

def read_results(filename):
    """
    读取指定算法的结果文件，并检查数据有效性。

    检查内容：
    1. OD 编号、起点和终点是否缺失；
    2. 路径、交通段数和总耗时是否缺失；
    3. 是否存在零耗时或负耗时；
    4. 是否存在不可达的 OD；
    5. 是否存在重复的 OD 编号。
    """

    # 指定本次分析需要读取的字段
    columns = [
        *KEY,
        "reachable",
        "path",
        "edge_count",
        "total_duration"
    ]

    # 读取 CSV 文件
    frame = pd.read_csv(
        RESULTS / filename,
        usecols=columns
    )

    # 统计各字段的缺失值数量
    missing = frame[columns].isna().sum()

    # 将总耗时转换为数值类型
    duration = pd.to_numeric(
        frame.total_duration,
        errors="coerce"
    )

    # 统计总耗时为 0 的记录
    zero = duration.eq(0).sum()

    # 统计缺失、非数值、负数或无穷大的耗时
    invalid = (
        duration.isna()
        | duration.lt(0)
        | duration.eq(float("inf"))
    ).sum()

    # 输出数据检查结果
    print(f"\n文件名称：{filename}")

    print(f"数据行数：{len(frame)}")

    print(f"字段缺失值总数：{missing.sum()}")

    print(f"零耗时记录数：{zero}")

    print(f"其他无效耗时记录数：{invalid}")

    # 如果数据存在异常，则停止分析
    if (
        missing.any()
        or zero
        or invalid
        or not frame.reachable.eq(True).all()
    ):

        raise ValueError(
            f"{filename} 存在缺失值、无效耗时或不可达 OD。\n"
            f"各字段缺失情况：{missing.to_dict()}"
        )

    # 检查 OD 编号是否唯一
    if not frame.pair_id.is_unique:

        raise ValueError(
            f"{filename} 存在重复的 pair_id"
        )

    # 返回检查后的结果
    return (
        frame
        .assign(total_duration=duration)
        .drop(columns="reachable")
    )


# ==================== 三、比较两种算法的结果 ====================

def main():

    print("\n========== 第一步：读取算法结果 ==========")

    # 读取 BFS 最少交通段数结果
    bfs = read_results(
        "bfs_results.csv"
    )

    # 读取 Dijkstra 最短耗时结果
    time = read_results(
        "dijkstra_time_results.csv"
    )

    print("\n两种算法的结果读取完成")

    print(f"BFS 结果数量：{len(bfs)}")

    print(f"Dijkstra 结果数量：{len(time)}")

    print("\n========== 第二步：检查 OD 对应关系 ==========")

    # 按照 pair_id 合并两种算法的结果
    # 使用 outer 确保任何缺失的 OD 都不会被忽略
    merged = bfs.merge(
        time,
        on="pair_id",
        how="outer",
        validate="one_to_one",
        suffixes=("_bfs", "_dijkstra"),
        indicator=True
    )

    # 检查两种算法的 OD 编号、起点和终点是否一致
    mismatches = merged.loc[

        merged._merge.ne("both")

        | merged.src_bfs.ne(merged.src_dijkstra)

        | merged.dst_bfs.ne(merged.dst_dijkstra),

        [
            "pair_id",
            "src_bfs",
            "dst_bfs",
            "src_dijkstra",
            "dst_dijkstra",
            "_merge"
        ],
    ]

    # 如果发现不一致，则输出具体记录并停止分析
    if not mismatches.empty:

        raise ValueError(
            "两种算法的 OD 编号或起点、终点不一致：\n"
            + mismatches.to_string(index=False)
        )

    # 检查合并后的 OD 数量
    if len(merged) != EXPECTED_OD_COUNT:

        raise ValueError(
            f"预期 OD 数量为 {EXPECTED_OD_COUNT}，"
            f"实际合并得到 {len(merged)} 对"
        )

    print("OD 编号检查通过")

    print("起点、终点一致性检查通过")

    print(f"合并后的 OD 数量：{len(merged)}")

    print("\n========== 第三步：筛选冲突 OD ==========")

    # 判断 BFS 的总耗时是否严格超过 Dijkstra 的两倍
    #
    # 判定公式：
    # BFS 总耗时 > 2 × Dijkstra 最短总耗时
    #
    # 使用原始数值进行比较，不提前进行四舍五入
    conflict = merged.loc[

        merged.total_duration_bfs.gt(
            2 * merged.total_duration_dijkstra
        )

    ].copy()

    # 计算 BFS 耗时与 Dijkstra 最短耗时的比值
    conflict["duration_ratio"] = (

        conflict.total_duration_bfs

        / conflict.total_duration_dijkstra

    )

    # 将 BFS 的起点和终点字段作为最终输出字段
    conflict = conflict.rename(
        columns={
            "src_bfs": "src",
            "dst_bfs": "dst"
        }
    )

    print(f"发现冲突 OD：{len(conflict)} 对")

    print("\n========== 第四步：整理冲突 OD 结果 ==========")

    # 指定最终 CSV 需要保存的字段
    fields = [

        *KEY,

        "path_bfs",

        "path_dijkstra",

        "edge_count_bfs",

        "edge_count_dijkstra",

        "total_duration_bfs",

        "total_duration_dijkstra",

        "duration_ratio",

    ]

    # 按照耗时比值从大到小排序
    # 如果比值相同，则按照 pair_id 从小到大排列
    conflict = conflict[fields].sort_values(

        ["duration_ratio", "pair_id"],

        ascending=[False, True]

    )

    # 保存冲突 OD 的详细结果
    output = RESULTS / "conflict_od_results.csv"

    conflict.to_csv(
        output,
        index=False,
        encoding="utf-8-sig"
    )

    print(f"冲突 OD 明细已保存：{output}")

    print("\n========== 第五步：统计整体实验结果 ==========")

    # 统计冲突 OD 数量及其占比
    conflict_count = len(conflict)

    conflict_ratio = (
        conflict_count / EXPECTED_OD_COUNT
    )

    # 计算全部 OD 的平均耗时
    bfs_mean = merged.total_duration_bfs.mean()

    time_mean = merged.total_duration_dijkstra.mean()

    print(f"\nOD 总数量：{len(merged)}")

    print(f"冲突 OD 数量：{conflict_count}")

    print(f"冲突比例：{conflict_ratio:.2%}")

    print(f"BFS 平均耗时：{bfs_mean:.2f} 分钟")

    print(
        f"Dijkstra 最短耗时平均值：{time_mean:.2f} 分钟"
    )

    print("\n========== 第六步：冲突 OD 耗时比值统计 ==========")

    # 统计冲突 OD 耗时比值的描述性统计指标
    print(
        conflict.duration_ratio.describe().to_string(
            float_format="{:.6f}".format
        )
    )

    print("\n========== 第七步：输出全部冲突 OD ==========")

    # 输出全部冲突 OD 的详细信息
    print(
        conflict.to_string(
            index=False,
            float_format="{:.6f}".format
        )
    )

    print("\n========== 第八步：筛选典型案例 ==========")

    # 选择耗时比值最高的前三对 OD
    top_three = conflict.head(3)

    print("\n耗时比值最高的三个案例：")

    print(
        top_three.to_string(
            index=False,
            float_format="{:.6f}".format
        )
    )

    print("\n========== 冲突分析完成 ==========")

    print(f"冲突 OD 结果文件：{output}")


# ==================== 九、程序入口 ====================

if __name__ == "__main__":

    main()
