
# -*- coding: utf-8 -*-
"""
执行 Q02 项目现有的数据清洗规则，并生成最终提交用的 Excel 统计表。

数据来源：
    data/raw/Q02_airports.csv
    data/raw/Q02_routes.csv
    data/raw/Q02_ground_links.csv
    data/raw/Q02_od_pairs.csv

清洗后数据：
    data/processed/routes_clean.csv
    data/processed/ground_links_clean.csv

输出文件：
    results/清洗前后统计表.xlsx
"""

from itertools import combinations
from pathlib import Path
from unicodedata import east_asian_width

import pandas as pd
from openpyxl import load_workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side


# ==================== 一、文件路径与基本参数 ====================

# 获取当前脚本所在项目的根目录
ROOT = Path(__file__).resolve().parents[1]

# 设置最终 Excel 文件的保存路径
OUTPUT = ROOT / "results" / "清洗前后统计表.xlsx"

# 设置本次作业的评测日期
DATE = pd.Timestamp("2026-01-15")

# 航线和地面接驳数据中的起点、终点字段
ENDPOINTS = ["src", "dst"]

# 不同季节代码对应的运营月份
MONTHS = {
    "ALL": range(1, 13),
    "DEC-FEB": (12, 1, 2),
    "APR-MAY": (4, 5),
    "JUN-AUG": (6, 7, 8),
    "SEP-OCT": (9, 10),
}


# ==================== 二、季节性航线判断 ====================

def in_season(frame):
    """
    判断航线在评测日期所在月份是否处于运营窗口。

    参数：
        frame：包含 seasonal 字段的数据表。

    返回：
        布尔序列，True 表示评测月份处于运营窗口，
        False 表示不在运营窗口或季节代码无法识别。
    """

    # 根据评测日期的月份与航线的季节代码进行匹配
    # 不认识的季节代码以及空值均视为不满足运营条件
    return frame.seasonal.map(
        lambda code: DATE.month in MONTHS.get(code, ())
    )


# ==================== 三、按照规则逐步执行数据清洗 ====================

def replay(table, frame, rules, details):
    """
    按照指定顺序重新执行数据清洗规则，并记录每一步的统计结果。

    参数：
        table：数据类别，例如航空或地面接驳。
        frame：待清洗的数据表。
        rules：清洗规则列表，每条规则包含名称和筛选条件。
        details：用于保存每一步清洗统计结果的列表。

    返回：
        完成全部清洗步骤后的数据表。
    """

    # 逐条执行清洗规则
    for number, (label, keep) in enumerate(rules, 1):

        # 根据当前规则筛选保留的数据
        retained = frame.loc[keep(frame)]

        # 记录当前步骤的输入数量、删除数量和保留数量
        # 每一步均以上一步保留的数据作为输入
        details.append([
            table,
            f"步骤 {number}",
            label,
            len(frame),
            len(frame) - len(retained),
            len(retained),
            "以上一步保留行为输入"
        ])

        # 将当前保留的数据作为下一步的输入
        frame = retained

    # 重置数据表索引并返回清洗结果
    return frame.reset_index(drop=True)


# ==================== 四、孤立机场统计 ====================

def isolated_count(ids, edges):
    """
    统计孤立机场数量。

    参数：
        ids：需要检查的机场 ID 集合。
        edges：当前图中的边，包含 src 和 dst 字段。

    返回：
        既没有入边，也没有出边的机场数量。
    """

    # 如果一个机场既没有作为边的起点，也没有作为边的终点，
    # 则认为该机场是孤立机场
    return len(ids - set(edges.src) - set(edges.dst))


# ==================== 五、Excel 表格格式设置 ====================

def style(sheet):
    """
    统一设置 Excel 工作表的显示格式。

    包括：
        1. 冻结首行。
        2. 开启自动筛选。
        3. 隐藏网格线。
        4. 设置表头颜色和字体。
        5. 设置单元格边框和对齐方式。
        6. 自动调整列宽。
        7. 设置打印页面布局。
    """

    # 冻结第一行，方便查看长表格时始终显示表头
    sheet.freeze_panes = "A2"

    # 为整个数据区域开启自动筛选
    sheet.auto_filter.ref = sheet.dimensions

    # 隐藏 Excel 默认网格线
    sheet.sheet_view.showGridLines = False

    # 设置打印页面适应纸张宽度
    sheet.sheet_properties.pageSetUpPr.fitToPage = True
    sheet.page_setup.orientation = "landscape"
    sheet.page_setup.fitToWidth = 1
    sheet.page_setup.fitToHeight = 0

    # 打印时重复显示第一行表头
    sheet.print_title_rows = "1:1"

    # 设置表头行高度
    sheet.row_dimensions[1].height = 25

    # 设置单元格下边框
    border = Border(
        bottom=Side(style="thin", color="DCE5EB")
    )

    # 遍历工作表中的每一列，统一设置格式
    for column in sheet.iter_cols():

        # 初始化当前列的最大宽度
        width = 0

        for cell in column:

            # 获取当前单元格内容
            value = "" if cell.value is None else str(cell.value)

            # 中文字符通常占两个字符宽度，英文和数字占一个字符宽度
            width = max(
                width,
                sum(
                    2 if east_asian_width(c) in "WF" else 1
                    for c in value
                )
            )

            # 判断当前单元格是否属于表头
            header = cell.row == 1

            # 判断当前单元格是否为数值类型
            numeric = cell.data_type == "n"

            # 设置字体
            cell.font = Font(
                name="Microsoft YaHei",
                size=10,
                bold=header,
                color="FFFFFF" if header else "183247"
            )

            # 设置背景颜色
            cell.fill = PatternFill(
                "solid",
                fgColor="244E69" if header else
                ("F1F6F9" if cell.row % 2 == 0 else "FFFFFF")
            )

            # 设置单元格边框
            cell.border = border

            # 设置垂直居中、自动换行以及对齐方式
            cell.alignment = Alignment(
                vertical="center",
                wrap_text=True,
                horizontal="right" if numeric and not header else "left"
            )

            # 数值型单元格使用千位分隔符显示
            if numeric and cell.value is not None:
                cell.number_format = "#,##0"

        # 根据内容长度自动调整列宽，并限制最大宽度
        sheet.column_dimensions[
            column[0].column_letter
        ].width = min(86, max(14, width + 5))

    # 统一设置数据行高度
    for row in range(2, sheet.max_row + 1):
        sheet.row_dimensions[row].height = 33


# ==================== 六、主程序：读取数据并执行统计 ====================

def main():

    # 设置原始数据和清洗后数据的文件夹路径
    raw = ROOT / "data" / "raw"
    processed = ROOT / "data" / "processed"

    # 依次读取四份原始数据
    airports, routes, ground, od = (
        pd.read_csv(raw / f"Q02_{name}.csv")
        for name in (
            "airports",
            "routes",
            "ground_links",
            "od_pairs"
        )
    )

    # 读取已经完成清洗的航空航线和地面接驳数据
    saved_routes = pd.read_csv(
        processed / "routes_clean.csv"
    )

    saved_ground = pd.read_csv(
        processed / "ground_links_clean.csv"
    )

    # 检查机场 ID 是否存在缺失或重复
    if (
        airports.airport_id.isna().any()
        or not airports.airport_id.is_unique
    ):
        raise ValueError("机场 ID 必须非空且唯一")

    # 获取全部登记机场 ID
    known = set(airports.airport_id)

    # 获取开放机场 ID，即 active=1 的机场
    active = set(
        airports.loc[
            airports.active.eq(1),
            "airport_id"
        ]
    )

    # 获取已关闭机场 ID，即 active=0 的机场
    closed = set(
        airports.loc[
            airports.active.eq(0),
            "airport_id"
        ]
    )

    # 判断一条边的起点和终点是否均为开放机场
    def active_endpoints(frame):
        return frame[ENDPOINTS].isin(active).all(axis=1)

    # 定义完全重复行删除规则
    # 只删除所有字段完全相同的重复记录
    deduplicate = (
        "删除完全重复行",
        lambda frame: ~frame.duplicated()
    )

    # 定义评测月份季节性筛选规则
    season = (
        "筛选评测月份",
        in_season
    )

    # 定义机场端点筛选规则
    endpoints = (
        "筛选双端开放机场",
        active_endpoints
    )

    # 创建列表，用于记录所有清洗步骤的统计信息
    details = []

    # 按照数据探查脚本的逻辑，
    # 先为航空航线添加评测月份是否可用的辅助字段
    routes_with_season = routes.assign(
        is_season_available=in_season(routes)
    )

    # ==================== 七、航空航线清洗 ====================

    # 按照既定顺序执行航空航线清洗
    clean_routes = replay(
        "航空",
        routes_with_season,
        [
            # 第一步：删除完全重复记录
            deduplicate,

            # 第二步：筛选评测月份仍在运营窗口内的航线
            season,

            # 第三步：仅保留起点和终点均为开放机场的航线
            endpoints,

            # 第四步：删除距离或耗时不大于零的航线
            (
                "筛选正距离及正耗时",
                lambda frame:
                frame.distance_km.gt(0)
                & frame.duration_min.gt(0)
            ),
        ],
        details
    )

    # ==================== 八、地面接驳清洗 ====================

    # 按照既定顺序执行地面接驳清洗
    clean_ground = replay(
        "地面",
        ground,
        [
            # 第一步：删除完全重复记录
            deduplicate,

            # 第二步：仅保留两端均为开放机场的接驳边
            endpoints,

            # 第三步：删除耗时不大于零的记录
            (
                "筛选正耗时",
                lambda frame: frame.duration_min.gt(0)
            ),

            # 第四步：根据评测日期筛选季节性接驳记录
            season,
        ],
        details
    )

    # ==================== 九、核对清洗结果 ====================

    # 将重新计算的清洗结果与现有清洗文件逐行、逐字段比较
    # 如果内容或顺序不一致，则立即报错
    pd.testing.assert_frame_equal(
        clean_routes,
        saved_routes
    )

    pd.testing.assert_frame_equal(
        clean_ground,
        saved_ground
    )

    # 合并航空边和地面接驳边的起点、终点信息
    clean_edges = pd.concat(
        [
            clean_routes[ENDPOINTS],
            clean_ground[ENDPOINTS]
        ],
        ignore_index=True
    )

    # 检查最终开放机场节点数、航空边数、地面边数和总边数
    if (
        len(active),
        len(clean_routes),
        len(clean_ground),
        len(clean_edges)
    ) != (612, 5191, 30, 5221):

        raise ValueError(
            "复算节点或边数与现有构图结果不一致"
        )

    # ==================== 十、统计清洗前的边与机场关系 ====================

    # 合并原始航空航线和原始地面接驳边
    raw_edges = pd.concat(
        [
            routes[ENDPOINTS],
            ground[ENDPOINTS]
        ],
        ignore_index=True
    )

    # 筛选起点和终点都能在机场原始表中找到的边
    known_edges = raw_edges.loc[
        raw_edges[ENDPOINTS].isin(known).all(axis=1)
    ]

    # 统计原始航空航线中两端均为开放机场的记录数量
    eligible_routes = int(
        active_endpoints(routes).sum()
    )

    # 统计原始地面接驳中两端均为开放机场的记录数量
    eligible_ground = int(
        active_endpoints(ground).sum()
    )

    # 合并两类原始数据中两端均为开放机场的边
    eligible_edges = raw_edges.loc[
        active_endpoints(raw_edges)
    ]

    # ==================== 十一、统计原始航空航线问题 ====================

    # 为原始航空数据建立不同问题的布尔标记
    flags = {

        # 完全重复行：除首次出现外的重复记录
        "完全重复额外行": routes.duplicated(),

        # 共享航班：codeshare 字段等于 1
        "共享航班": routes.codeshare.eq(1),

        # 非评测月份航线：评测日期不在运营窗口内
        "非评测月航线": ~in_season(routes),

        # 涉及关闭机场：起点或终点属于已关闭机场
        "涉及关闭机场":
            routes[ENDPOINTS].isin(closed).any(axis=1),

        # 涉及不存在机场：起点或终点未登记在机场原始表中
        "涉及不存在机场":
            (~routes[ENDPOINTS].isin(known)).any(axis=1),

        # 任一端点不是开放机场
        "任一端点非开放机场":
            ~active_endpoints(routes),
    }

    # 获取已经去重并完成季节筛选的航空航线
    # 这些记录即将进入机场端点筛选步骤
    stage_two = (
        routes
        .drop_duplicates()
        .loc[lambda frame: in_season(frame)]
    )

    # 记录各类问题在原始航空数据中的命中数量
    # 注意：这些标记可能发生重叠，不能直接相加
    for label, mask in flags.items():

        details.append([
            "航空",
            "原始标记",
            label,
            len(routes),
            None,
            int(mask.sum()),
            "末列数值为命中行数，各标记允许重叠"
        ])

    # 选择需要进行交集分析的三类问题
    overlap_flags = [
        "完全重复额外行",
        "共享航班",
        "任一端点非开放机场"
    ]

    # 统计上述问题两两交集以及三者同时命中的记录数量
    for labels in [
        *combinations(overlap_flags, 2),
        tuple(overlap_flags)
    ]:

        # 只有同时满足所有指定条件的记录才会被统计
        count = int(
            pd.concat(
                [flags[label] for label in labels],
                axis=1
            ).all(axis=1).sum()
        )

        details.append([
            "航空",
            "原始交集",
            " ∩ ".join(labels),
            len(routes),
            None,
            count,
            "同一原始行同时命中全部列示标记"
        ])

    # 统计完全重复、共享航班和非开放机场端点的并集
    # 同一条记录即使命中多个问题，也只计数一次
    union = int(
        pd.concat(
            [flags[label] for label in overlap_flags],
            axis=1
        ).any(axis=1).sum()
    )

    details.append([
        "航空",
        "原始并集",
        "重复额外行、共享或非开放端点",
        len(routes),
        None,
        union,
        "命中任一标记即计一次，共享标志本身不触发删除"
    ])

    # 检查关闭机场与不存在机场是否同时出现在同一条原始航线上
    details.append([
        "航空",
        "原始交集",
        "关闭端点 ∩ 不存在端点",
        len(routes),
        None,
        int(
            (
                flags["涉及关闭机场"]
                & flags["涉及不存在机场"]
            ).sum()
        ),
        "每条原始航线最多计一次"
    ])

    # 统计航空去重且筛选月份后，进入端点筛选之前的问题记录
    for label in (
        "涉及关闭机场",
        "涉及不存在机场",
        "任一端点非开放机场"
    ):

        details.append([
            "航空",
            "端点筛选前",
            label,
            len(stage_two),
            None,
            int(flags[label].loc[stage_two.index].sum()),
            "航空去重且筛选月份后的命中数"
        ])

    # 进一步统计不同清洗问题之间的重叠关系
    details.extend([

        # 统计完全重复且不在评测月份运营的记录
        [
            "航空",
            "原始交集",
            "完全重复额外行 ∩ 非评测月航线",
            len(routes),
            None,
            int(
                (
                    flags["完全重复额外行"]
                    & flags["非评测月航线"]
                ).sum()
            ),
            "这些记录先因完全重复被删除"
        ],

        # 统计负距离且端点无效的记录
        [
            "航空",
            "端点筛选前",
            "负距离 ∩ 非开放端点",
            len(stage_two),
            None,
            int(
                (
                    stage_two.distance_km.lt(0)
                    & ~active_endpoints(stage_two)
                ).sum()
            ),
            "这些记录先因机场端点无效被删除"
        ],
    ])

    # ==================== 十二、生成清洗前后统计汇总表 ====================

    summary = [

        # 机场节点数量统计
        [
            "机场节点",
            len(known),
            len(active),
            len(known) - len(active),
            "构图仅纳入 active=1 的机场"
        ],

        # 航空航线数量统计
        [
            "航空记录／候选边",
            len(routes),
            len(clean_routes),
            len(routes) - len(clean_routes),
            "每条记录计一条有向边"
        ],

        # 地面接驳数量统计
        [
            "地面接驳记录／候选边",
            len(ground),
            len(clean_ground),
            len(ground) - len(clean_ground),
            "每条记录计一条有向边"
        ],

        # 航空边与地面接驳边合计
        [
            "航空及地面候选边合计",
            len(raw_edges),
            len(clean_edges),
            len(raw_edges) - len(clean_edges),
            "原始候选含无效端点及重复行"
        ],

        # 两端均已在机场原始表登记的边
        [
            "双端已登记的边",
            len(known_edges),
            len(clean_edges),
            None,
            "清洗前按所有登记机场检查端点"
        ],

        # 两端均为开放机场的航空边
        [
            "双端开放可接入的航空边",
            eligible_routes,
            len(clean_routes),
            None,
            "清洗前仅验证节点资格"
        ],

        # 两端均为开放机场的地面接驳边
        [
            "双端开放可接入的地面边",
            eligible_ground,
            len(clean_ground),
            None,
            "清洗前仅验证节点资格"
        ],

        # 两端均为开放机场的边合计
        [
            "双端开放可接入的边合计",
            len(eligible_edges),
            len(clean_edges),
            None,
            "清洗前仍含重复、非当季及权重异常记录"
        ],

        # 使用各阶段对应的节点集合统计孤立机场
        [
            "孤立机场（各阶段节点集）",
            isolated_count(known, known_edges),
            isolated_count(active, clean_edges),
            None,
            "入度与出度均为零。前用已登记节点，后用开放节点"
        ],

        # 使用固定的开放机场节点集合统计孤立机场
        [
            "孤立机场（固定开放节点集）",
            isolated_count(active, eligible_edges),
            isolated_count(active, clean_edges),
            None,
            "两阶段均以开放机场为节点"
        ],

        # OD 数据仅用于路径评价，不参与建图
        [
            "OD 输入记录",
            len(od),
            len(od),
            0,
            "OD 用于评价，未作为图边或执行清洗"
        ],

        # 统计同向机场对的重复记录
        [
            "同向机场对重复额外行",
            int(routes.duplicated(ENDPOINTS).sum()),
            int(clean_routes.duplicated(ENDPOINTS).sum()),
            None,
            "同向机场对保留首条后其余行，可有不同服务"
        ],
    ]

    # ==================== 十三、统计清洗后各类问题 ====================

    # 对清洗后的航空航线重新检查各类问题
    after_flags = {

        # 检查是否还存在完全重复记录
        "完全重复额外行": clean_routes.duplicated(),

        # 检查是否还存在共享航班
        "共享航班": clean_routes.codeshare.eq(1),

        # 检查是否还存在非评测月份航线
        "非评测月航线": ~in_season(clean_routes),

        # 检查是否还存在涉及关闭机场的航线
        "涉及关闭机场":
            clean_routes[ENDPOINTS].isin(closed).any(axis=1),

        # 检查是否还存在涉及不存在机场的航线
        "涉及不存在机场":
            (~clean_routes[ENDPOINTS].isin(known)).any(axis=1),

        # 检查是否还存在非开放机场端点
        "任一端点非开放机场":
            ~active_endpoints(clean_routes),
    }

    # 将清洗前后的问题数量加入统计汇总表
    for label, mask in flags.items():

        summary.append([
            label,
            int(mask.sum()),
            int(after_flags[label].sum()),

            # 完全重复额外行的命中数即为删除数量
            int(mask.sum())
            if label == "完全重复额外行"
            else None,

            # 共享航班不是实际删除条件，需单独说明
            "codeshare=1，未作为筛选条件"
            if label == "共享航班"
            else "分别在原表和清洗表独立计数，实际删除数见明细"
        ])

    # ==================== 十四、记录数据来源与统计口径 ====================

    sources = [

        [
            "评测日期",
            "2026-01-15",
            "现有代码仅依据评测月份 1 月过滤"
        ],

        [
            "原始机场",
            "data/raw/Q02_airports.csv",
            "机场 ID 唯一，以 active=1 确定构图节点"
        ],

        [
            "原始航线",
            "data/raw/Q02_routes.csv",
            "航空逐行计数，保留不同服务的并行边"
        ],

        [
            "原始接驳",
            "data/raw/Q02_ground_links.csv",
            "地面接驳逐行计数，无原始距离字段"
        ],

        [
            "原始 OD",
            "data/raw/Q02_od_pairs.csv",
            "仅作为评测查询"
        ],

        [
            "清洗航线",
            "data/processed/routes_clean.csv",
            "复算后逐字段、逐行顺序一致"
        ],

        [
            "清洗接驳",
            "data/processed/ground_links_clean.csv",
            "复算后逐字段、逐行顺序一致"
        ],

        [
            "清洗规则",
            "scripts/01_data_explore.py",
            "航空和地面分别按原脚本步骤顺序复算"
        ],

        [
            "建图规则",
            "scripts/02_graph_builder.py",
            "612 个开放节点、5191 条航空边、30 条地面边"
        ],

        [
            "里程口径",
            "航空 CSV 里程；地面 Haversine",
            "大圆代理里程在构图时计算，无地面距离过滤"
        ],

        [
            "季节口径",
            "ALL、DEC-FEB 覆盖 1 月",
            "其余已知月份窗口与未知或空值均不通过"
        ],

        [
            "原始命中与删除",
            "原始标记可重叠；实际步骤互斥",
            "明细的标记行展示命中数，只有步骤行的删除数可相加"
        ],

        [
            "字段语义",
            "codeshare 与 stops",
            "共享按代码中的 1 计数；承运关系和 stops 业务含义待核实"
        ],
    ]

    # ==================== 十五、创建三个 Excel 工作表 ====================

    sheets = {

        # 工作表一：清洗前后统计汇总
        "清洗前后统计汇总": pd.DataFrame(
            summary,
            columns=[
                "统计项目",
                "清洗前",
                "清洗后",
                "删除或排除数",
                "统计说明"
            ]
        ),

        # 工作表二：清洗项目明细
        "清洗项目明细": pd.DataFrame(
            details,
            columns=[
                "数据类别",
                "统计阶段",
                "项目",
                "输入行数",
                "实际删除数",
                "保留或命中数",
                "统计说明"
            ]
        ),

        # 工作表三：数据来源与统计口径
        "数据来源与统计口径": pd.DataFrame(
            sources,
            columns=[
                "主题",
                "文件或规则",
                "说明"
            ]
        ),
    }

    # ==================== 十六、导出 Excel 文件 ====================

    # 使用 openpyxl 作为 Excel 写入引擎
    with pd.ExcelWriter(
        OUTPUT,
        engine="openpyxl"
    ) as writer:

        # 依次将三个统计表写入不同工作表
        for name, frame in sheets.items():

            frame.to_excel(
                writer,
                sheet_name=name,
                index=False
            )

            # 为当前工作表应用统一格式
            style(writer.sheets[name])

    # ==================== 十七、重新打开 Excel 并进行验收 ====================

    # 重新读取刚刚生成的 Excel 文件
    workbook = load_workbook(OUTPUT)

    try:

        # 检查工作表名称和数量是否正确
        assert workbook.sheetnames == list(sheets)

        # 逐个检查工作表
        for name, frame in sheets.items():

            sheet = workbook[name]

            # 检查是否冻结首行，以及是否开启自动筛选
            assert (
                sheet.freeze_panes == "A2"
                and sheet.auto_filter.ref == sheet.dimensions
            )

            # 将 Excel 中实际保存的数据重新转换为 DataFrame
            # 与生成前的数据逐项比较，检查导出结果是否完整
            pd.testing.assert_frame_equal(
                pd.DataFrame(
                    list(sheet.values)[1:],
                    columns=frame.columns
                ),
                frame,
                check_dtype=False
            )

    finally:

        # 无论验收成功与否，都关闭 Excel 文件
        workbook.close()

    # ==================== 十八、输出统计结果 ====================

    # 在终端打印清洗前后统计汇总表
    print("\n========== 清洗前后统计汇总 ==========")

    print(
        sheets["清洗前后统计汇总"].to_string(index=False)
    )

    # 在终端打印清洗项目明细表
    print("\n========== 清洗项目明细 ==========")

    print(
        sheets["清洗项目明细"].to_string(index=False)
    )

    # 输出最终验收结果和文件保存路径
    print(
        f"\n验收通过，三个工作表重新打开成功，"
        f"最终图边数 {len(clean_edges)}。"
    )

    print(f"Excel 文件已保存至：{OUTPUT}")


# ==================== 十九、程序入口 ====================

if __name__ == "__main__":
    main()
