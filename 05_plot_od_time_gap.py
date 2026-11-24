
# -*- coding: utf-8 -*-
"""
绘制 Q02 中 200 对 OD 的耗时差距分布图。

数据来源：
    results/bfs_results.csv
    results/dijkstra_time_results.csv

输出文件：
    figures/Q02_200对OD耗时差距分布图.png
"""

import os
from pathlib import Path

import matplotlib
matplotlib.use("Agg")

import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.ticker import MaxNLocator
import numpy as np
import pandas as pd


# ==================== 一、文件路径与基本参数 ====================

# 获取项目根目录
PROJECT_ROOT = Path(__file__).resolve().parents[1]

# 算法结果 CSV 所在目录
RESULTS = PROJECT_ROOT / "results"

# 图片输出目录
FIGURES = PROJECT_ROOT / "figures"

# 设置图片输出路径
OUTPUT = FIGURES / "Q02_200对OD耗时差距分布图.png"

# 如果 figures 目录不存在，则自动创建
FIGURES.mkdir(parents=True, exist_ok=True)

# 本次实验共有 200 对 OD
OD_COUNT = 200


# ==================== 二、读取并检查算法结果 ====================

def read_results(filename):
    """
    读取算法结果，并检查数据完整性。

    参数：
        filename：结果 CSV 文件名称。

    返回：
        经过检查和类型转换的数据表。
    """

    # 只读取本次分析需要的字段
    columns = [
        "pair_id",
        "src",
        "dst",
        "reachable",
        "total_duration"
    ]

    frame = pd.read_csv(RESULTS / filename, usecols=columns)

    # 检查记录数量、OD 编号唯一性以及字段缺失情况
    if (
        len(frame) != OD_COUNT
        or not frame.pair_id.is_unique
        or frame.isna().any().any()
    ):
        raise ValueError(
            f"{filename} 必须包含 200 个唯一 OD，"
            "且检查字段不得缺失"
        )

    # 将总耗时转换为数值类型
    duration = pd.to_numeric(
        frame.total_duration,
        errors="coerce"
    )

    # 检查是否存在不可达 OD、无效耗时或非正耗时
    if (
        not frame.reachable.eq(True).all()
        or not (np.isfinite(duration) & duration.gt(0)).all()
    ):
        raise ValueError(
            f"{filename} 存在不可达 OD 或无效耗时"
        )

    # 返回处理后的数据，并移除不再需要的可达状态字段
    return frame.assign(
        total_duration=duration
    ).drop(columns="reachable")


# ==================== 三、数据合并与指标计算 ====================

def main():

    # 分别读取 BFS 和 Dijkstra 最短耗时算法的结果
    bfs = read_results("bfs_results.csv")
    time = read_results("dijkstra_time_results.csv")

    # 按照 pair_id 合并两种算法的结果
    # 使用外连接，防止某些 OD 编号未匹配而被自动丢弃
    pairs = bfs.merge(
        time,
        on="pair_id",
        how="outer",
        validate="one_to_one",
        suffixes=("_bfs", "_time"),
        indicator=True
    )

    # 检查两种算法的 OD 编号、起点和终点是否完全一致
    if not (
        pairs._merge.eq("both")
        & pairs.src_bfs.eq(pairs.src_time)
        & pairs.dst_bfs.eq(pairs.dst_time)
    ).all():
        raise ValueError(
            "两份结果的 OD 编号或起终点不一致"
        )

    # 提取两种算法的总耗时
    bfs_time = pairs.total_duration_bfs
    shortest = pairs.total_duration_time

    # 计算每对 OD 通过最短耗时算法节省的时间
    # 节省时间 = BFS 耗时 - Dijkstra 最短耗时
    saved = bfs_time - shortest

    # 计算两种算法的耗时比值
    # 耗时比 = BFS 耗时 / Dijkstra 最短耗时
    ratio = bfs_time / shortest

    # 检查 BFS 耗时是否小于 Dijkstra 最短耗时
    # 正常情况下，最短耗时算法不应出现这种情况
    if saved.lt(0).any():
        raise ValueError(
            "存在 BFS 耗时小于 Dijkstra 最短耗时的记录"
        )

    # 统计 BFS 耗时严格超过最短耗时两倍的 OD 数量
    conflicts = int(
        bfs_time.gt(2 * shortest).sum()
    )

    # 计算冲突 OD 占全部 200 对 OD 的比例
    share = conflicts / len(pairs)

    # 输出主要统计指标
    print(f"OD 总数量 {len(pairs)}")
    print(f"BFS 平均耗时 {bfs_time.mean():.2f} 分钟")
    print(f"Dijkstra 平均耗时 {shortest.mean():.2f} 分钟")
    print(f"平均节省时间 {saved.mean():.2f} 分钟")
    print(f"平均耗时比 {ratio.mean():.4f}")
    print(
        f"耗时比严格大于 2 的 OD {conflicts} 对，"
        f"占 {share:.2%}"
    )

    # ==================== 四、历史统计结果核验 ====================

    # 将计算结果按照指定显示精度与历史统计进行比较
    # 注意：这里只在核验时格式化，实际计算仍使用原始精度
    if (
        f"{bfs_time.mean():.2f}",
        f"{shortest.mean():.2f}",
        conflicts,
        f"{share:.2%}"
    ) != (
        "2265.97",
        "1427.43",
        49,
        "24.50%"
    ):
        raise ValueError(
            "核验值与历史统计不一致，请检查结果文件及统计口径"
        )

    # ==================== 五、中文字体设置 ====================

    # 获取 Windows 系统字体目录
    font_dir = Path(
        os.environ.get("WINDIR", "C:/Windows")
    ) / "Fonts"

    # 优先使用微软雅黑，若不存在则使用黑体
    font = next(
        (
            font_dir / name
            for name in ("msyh.ttc", "simhei.ttf")
            if (font_dir / name).is_file()
        ),
        None
    )

    # 如果没有找到中文字体，则停止绘图
    if font is None:
        raise RuntimeError(
            "未找到微软雅黑或黑体字体"
        )

    # 将找到的字体添加到 Matplotlib
    font_manager.fontManager.addfont(str(font))

    # 设置全局绘图参数
    plt.rcParams.update({
        "font.family": font_manager.FontProperties(
            fname=font
        ).get_name(),

        "font.size": 11,

        # 隐藏图表上边框和右边框
        "axes.spines.top": False,
        "axes.spines.right": False,

        # 设置坐标轴颜色
        "axes.edgecolor": "#657587",

        # 将网格线放在数据图形下方
        "axes.axisbelow": True,

        # 正常显示负号
        "axes.unicode_minus": False,

        # 设置图片背景为白色
        "figure.facecolor": "white",
    })

    # ==================== 六、创建画布 ====================

    # 创建一张包含两个并排子图的画布
    fig, (left, right) = plt.subplots(
        1,
        2,
        figsize=(12, 5.1),
        layout="constrained"
    )

    # 设置整张图的总标题
    fig.suptitle(
        "Q02 三种路线优化口径中的耗时差距分析",
        fontsize=17,
        fontweight="bold"
    )

    # ==================== 七、左图：节省时间分布 ====================

    # 使用直方图展示 200 对 OD 的节省时间分布
    left.hist(
        saved,
        bins=np.arange(
            0,
            saved.max() + 250,
            250
        ),
        color="#527FA5",
        edgecolor="white",
        linewidth=0.8
    )

    # 添加平均节省时间的垂直虚线
    left.axvline(
        saved.mean(),
        color="#154B68",
        linestyle="--",
        linewidth=1.8,
        label=f"平均节省时间  {saved.mean():,.2f} 分钟"
    )

    # 设置左图标题和横坐标名称
    left.set(
        title="200 对 OD 的节省时间分布",
        xlabel="节省时间（分钟）"
    )

    # ==================== 八、右图：耗时比值分布 ====================

    # 使用直方图展示 BFS 与 Dijkstra 的耗时比值分布
    right.hist(
        ratio,
        bins=np.arange(
            1,
            ratio.max() + 0.25,
            0.25
        ),
        color="#4B8E89",
        edgecolor="white",
        linewidth=0.8
    )

    # 添加 x=1 参考线，表示两种算法耗时相同
    right.axvline(
        1,
        color="#536273",
        linewidth=1.7,
        label="耗时相等  x=1"
    )

    # 添加 x=2 红色虚线，表示两倍耗时冲突阈值
    right.axvline(
        2,
        color="#C43C3C",
        linestyle="--",
        linewidth=1.8,
        label="冲突阈值  x=2"
    )

    # 添加平均耗时比参考线
    right.axvline(
        ratio.mean(),
        color="#164C53",
        linestyle="-.",
        linewidth=1.7,
        label=f"平均耗时比  {ratio.mean():.4f}"
    )

    # 设置右图标题和横坐标名称
    right.set(
        title="200 对 OD 的耗时比值分布",
        xlabel="耗时比值（BFS / Dijkstra）"
    )

    # ==================== 九、统一图表格式 ====================

    for axis in (left, right):

        # 设置纵坐标名称
        axis.set_ylabel("OD 数量")

        # 纵坐标刻度设置为整数
        axis.yaxis.set_major_locator(
            MaxNLocator(integer=True)
        )

        # 添加浅色横向网格线
        axis.grid(
            axis="y",
            color="#E4EAF0",
            linewidth=0.8
        )

        # 显示图例
        axis.legend(
            loc="upper right",
            frameon=True,
            facecolor="white",
            edgecolor="#E4EAF0"
        )

    # ==================== 十、保存图片 ====================

    # 以 300 DPI 分辨率保存 PNG 图片
    fig.savefig(
        OUTPUT,
        dpi=300,
        facecolor="white"
    )

    # 释放绘图资源
    plt.close(fig)

    # 输出最终文件保存位置
    print(f"PNG 已保存 {OUTPUT}")


# 程序入口
if __name__ == "__main__":
    main()
