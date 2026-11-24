import pandas as pd

# 1. 读取 CSV 文件
airports = pd.read_csv("../data/raw/Q02_airports.csv")
routes = pd.read_csv("../data/raw/Q02_routes.csv")
ground = pd.read_csv("../data/raw/Q02_ground_links.csv")
od = pd.read_csv("../data/raw/Q02_od_pairs.csv")

#检查airports表
# 2. 查看字段名称
print("机场表字段：")
print(airports.columns.tolist())

# 3. 查看数据类型
print("\n机场表数据类型：")
print(airports.dtypes)

# 4. 查看前5行样例
print("\n机场表前5行：")
print(airports.head())

# 5. 查看数据规模
print("\n机场表数据规模：")
print(airports.shape)

# 6. 查看缺失值
print("\n机场表缺失值：")
print(airports.isnull().sum())

# 7. 查看数值统计
print("\n机场表数值统计：")
print(airports.describe())

# 8. 查看重复行
print("\n机场表重复行数量：")
print(airports.duplicated().sum())

# 9. 统计机场运营状态
print("\n机场运营状态统计：")
print(airports["active"].value_counts())

# 统计比例
print("\n机场运营状态比例：")
print(airports["active"].value_counts(normalize=True))

# 10. 检查机场ID重复
print("\n机场ID重复数量：")
print(airports["airport_id"].duplicated().sum())

# 查看重复的机场ID记录
print("\n重复机场ID对应的记录：")
print(
    airports[
        airports["airport_id"].duplicated(keep=False)
    ]
)

# 11. 统计机场类型
print("\n机场类型统计：")
print(airports["type"].value_counts())

# 12. 检查经纬度异常

invalid_lat = airports[
    (airports["lat"] < -90) |
    (airports["lat"] > 90)
]

invalid_lon = airports[
    (airports["lon"] < -180) |
    (airports["lon"] > 180)
]

print("\n纬度异常数量：", len(invalid_lat))
print("经度异常数量：", len(invalid_lon))

# 将航线表与机场表关联，获取起点城市

routes_with_src = routes.merge(
    airports[["airport_id", "city"]],
    left_on="src",
    right_on="airport_id",
    how="left"
)

print(routes_with_src.head())


# 13. 检查机场ID是否唯一
print("\n机场ID唯一性：")
print(airports["airport_id"].is_unique)

# 14. 检查航线起点是否都存在于机场表
valid_airport_ids = set(airports["airport_id"])

invalid_src = routes[
    ~routes["src"].isin(valid_airport_ids)
]

print("\n不存在的航线起点数量：")
print(len(invalid_src))

# 15. 检查航线终点是否都存在于机场表
invalid_dst = routes[
    ~routes["dst"].isin(valid_airport_ids)
]

print("\n不存在的航线终点数量：")
print(len(invalid_dst))

# 16. 检查地面接驳起点和终点
invalid_ground_src = ground[
    ~ground["src"].isin(valid_airport_ids)
]

invalid_ground_dst = ground[
    ~ground["dst"].isin(valid_airport_ids)
]

print("\n不存在的地面接驳起点数量：")
print(len(invalid_ground_src))

print("不存在的地面接驳终点数量：")
print(len(invalid_ground_dst))


# 检查routes表

# 17. 查看 stops 的取值分布
print("\n航线经停次数分布：")
print(routes["stops"].value_counts(dropna=False).sort_index())

# 18. 查看 codeshare 的取值分布
print("\n共享航班分布：")
print(routes["codeshare"].value_counts(dropna=False))

# 19. 查看 seasonal 的取值分布
print("\n季节性航线分布：")
print(routes["seasonal"].value_counts(dropna=False))

# 20. 查看三种字段的组合
print("\nstops、codeshare、seasonal 组合统计：")
print(
    routes.groupby(
        ["stops", "codeshare", "seasonal"],
        dropna=False
    ).size().reset_index(name="count")
)


# 21. 提取不存在的终点机场记录

invalid_dst = routes[
    ~routes["dst"].isin(valid_airport_ids)
]

print("\n不存在的终点机场记录：")
print(invalid_dst)

# 22. 统计涉及多少个不同的无效机场ID

print("\n无效终点机场ID：")
print(invalid_dst["dst"].unique())

print("\n无效终点机场ID数量：")
print(invalid_dst["dst"].nunique())

# 23. 统计每个无效机场ID出现的次数

print("\n无效终点机场出现频率：")
print(invalid_dst["dst"].value_counts())


# 24. 获取关闭机场ID集合

closed_airport_ids = set(
    airports.loc[
        airports["active"] == 0,
        "airport_id"
    ]
)

print("\n关闭机场数量：")
print(len(closed_airport_ids))

# 25. 检查航线起点是否为关闭机场

closed_src = routes[
    routes["src"].isin(closed_airport_ids)
]

# 26. 检查航线终点是否为关闭机场

closed_dst = routes[
    routes["dst"].isin(closed_airport_ids)
]

print("\n连接关闭机场的航线起点记录数：")
print(len(closed_src))

print("\n连接关闭机场的航线终点记录数：")
print(len(closed_dst))

# 27. 检查地面接驳

closed_ground_src = ground[
    ground["src"].isin(closed_airport_ids)
]

closed_ground_dst = ground[
    ground["dst"].isin(closed_airport_ids)
]

print("\n连接关闭机场的地面接驳起点记录数：")
print(len(closed_ground_src))

print("\n连接关闭机场的地面接驳终点记录数：")
print(len(closed_ground_dst))


# 28. 经停次数分布

print("\n========== 经停次数分布 ==========")
print(routes["stops"].value_counts(dropna=False).sort_index())

# 29. 代码共享分布

print("\n========== 代码共享分布 ==========")
print(routes["codeshare"].value_counts(dropna=False))

# 30. 季节性航线分布

print("\n========== 季节性航线分布 ==========")
print(routes["seasonal"].value_counts(dropna=False))

# 31. 查看季节性航线所有取值

print("\n========== 季节性航线所有类别 ==========")
print(routes["seasonal"].unique())

# 32. 查看航线耗时和距离统计

print("\n========== 航线距离统计 ==========")
print(routes["distance_km"].describe())

print("\n========== 航线耗时统计 ==========")
print(routes["duration_min"].describe())


# 33. 检查航线距离异常

print("\n========== 距离异常检查 ==========")

# 检查负数距离
negative_distance = routes[
    routes["distance_km"] < 0
]

# 检查零距离
zero_distance = routes[
    routes["distance_km"] == 0
]

# 检查缺失距离
missing_distance = routes[
    routes["distance_km"].isnull()
]

print("负数距离记录数：", len(negative_distance))
print("零距离记录数：", len(zero_distance))
print("缺失距离记录数：", len(missing_distance))

# 打印异常记录
print("\n负数距离记录：")
print(negative_distance[
    ["src", "dst", "airline", "distance_km", "duration_min"]
])


# 34. 检查航班耗时异常

print("\n========== 耗时异常检查 ==========")

# 负数耗时
negative_duration = routes[
    routes["duration_min"] < 0
]

# 零耗时
zero_duration = routes[
    routes["duration_min"] == 0
]

# 缺失耗时
missing_duration = routes[
    routes["duration_min"].isnull()
]

print("负数耗时记录数：", len(negative_duration))
print("零耗时记录数：", len(zero_duration))
print("缺失耗时记录数：", len(missing_duration))

print("\n负数耗时记录：")
print(negative_duration)


# 35. 使用IQR方法检查距离异常值

Q1 = routes["distance_km"].quantile(0.25)
Q3 = routes["distance_km"].quantile(0.75)

IQR = Q3 - Q1

lower = Q1 - 1.5 * IQR
upper = Q3 + 1.5 * IQR

print("\n========== IQR距离异常检测 ==========")

print("Q1：", Q1)
print("Q3：", Q3)
print("IQR：", IQR)
print("下界：", lower)
print("上界：", upper)

distance_outliers = routes[
    (routes["distance_km"] < lower) |
    (routes["distance_km"] > upper)
]

print("\n潜在异常距离记录数：", len(distance_outliers))

print("\n潜在异常记录：")
print(distance_outliers[
    ["src", "dst", "distance_km", "duration_min"]
].head(20))


# 38. 检查航线表完全重复行

print("\n========== 完全重复行检查 ==========")

duplicate_rows = routes[
    routes.duplicated(keep=False)
]

print("完全重复行涉及的记录数：", len(duplicate_rows))

print("\n重复记录样例：")
print(duplicate_rows.head(20))


# 39. 检查同一机场对的航线数量

print("\n========== 同一机场对统计 ==========")

route_pairs = routes.groupby(
    ["src", "dst"]
).size().reset_index(name="route_count")

print("不同机场对数量：", len(route_pairs))

# 找出存在多条记录的机场对
multi_routes = route_pairs[
    route_pairs["route_count"] > 1
]

print("存在多条航线记录的机场对数量：", len(multi_routes))

print("\n多航线记录的机场对：")
print(multi_routes.head(20))


# 40. 检查共享航班记录

print("\n========== 共享航班检查 ==========")

# 统计共享航班数量
print("codeshare=1 的记录数：")
print((routes["codeshare"] == 1).sum())

# 查看共享航班样例
shared_routes = routes[
    routes["codeshare"] == 1
]

print("\n共享航班样例：")
print(shared_routes.head(20))

# 查看共享航班涉及的机场对
shared_pairs = shared_routes.groupby(
    ["src", "dst"]
).size().reset_index(name="shared_count")

print("\n共享航班涉及的不同机场对数量：")
print(len(shared_pairs))


# 完全重复行的进一步分析

# 重复组涉及的全部记录
duplicate_all = routes[
    routes.duplicated(keep=False)
]

# 真正多出来的重复记录（保留第一条）
duplicate_extra = routes[
    routes.duplicated(keep="first")
]

print("重复组涉及记录数：", len(duplicate_all))
print("多出来的重复记录数：", len(duplicate_extra))

# 检查ground表
# 统计有多少组完全重复记录
duplicate_groups = (
    routes.groupby(list(routes.columns), dropna=False)
    .size()
    .reset_index(name="count")
)

duplicate_groups = duplicate_groups[
    duplicate_groups["count"] > 1
]

print("完全重复的数据组数：", len(duplicate_groups))

print("\n重复数据组样例：")
print(duplicate_groups.head(10))


# 分析包含共享航班的机场对

pair_analysis = routes.groupby(
    ["src", "dst"]
).agg(
    total_routes=("src", "size"),
    airline_count=("airline", "nunique"),
    codeshare_count=("codeshare", "sum"),
    distance_count=("distance_km", "nunique"),
    duration_count=("duration_min", "nunique")
).reset_index()

# 找出存在共享航班标记的机场对
codeshare_analysis = pair_analysis[
    pair_analysis["codeshare_count"] > 0
]

print("\n共享航班机场对分析：")
print(codeshare_analysis.head(20))

print("\n包含共享航班标记的机场对数量：")
print(len(codeshare_analysis))

# 查看共享航班机场对的记录数分布
print("\n每个机场对的航线数量分布：")
print(codeshare_analysis["total_routes"].value_counts().sort_index())


# 41. 地面接驳数据分析

print("\n========== 地面接驳数据分析 ==========")

# 1. 查看全部30条记录
print("\n地面接驳全部记录：")
print(ground.to_string(index=False))

# 2. 查看交通方式分布
print("\n交通方式分布：")
print(ground["mode"].value_counts())

# 3. 查看地面接驳耗时统计
print("\n接驳耗时统计：")
print(ground["duration_min"].describe())

# 4. 查看stops分布
print("\n中途停靠站数量分布：")
print(ground["stops"].value_counts().sort_index())

# 5. 查看季节性分布
print("\n地面接驳季节分布：")
print(ground["seasonal"].value_counts())

# 6. 检查完全重复记录
print("\n完全重复记录数：")
print(ground.duplicated().sum())

# 7. 检查相同机场对
ground_pairs = ground.groupby(
    ["src", "dst"]
).size().reset_index(name="count")

print("\n地面接驳不同机场对数量：", len(ground_pairs))

print("\n存在多条接驳记录的机场对：")
print(ground_pairs[ground_pairs["count"] > 1])

# 8. 查看接驳耗时最长的记录
print("\n耗时最长的5条地面接驳：")
print(
    ground.nlargest(5, "duration_min")
)


# 42. 季节性航线分析

print("\n========== 季节性航线筛选 ==========")

# 评测日期为1月15日
evaluation_month = 1

# 定义各季节运营月份
season_months = {
    "ALL": list(range(1, 13)),
    "DEC-FEB": [12, 1, 2],
    "JUN-AUG": [6, 7, 8],
    "SEP-OCT": [9, 10],
    "APR-MAY": [4, 5]
}

# 判断每条航线在评测日期是否运营
routes["is_season_available"] = routes["seasonal"].apply(
    lambda x: evaluation_month in season_months.get(x, [])
)

print("评测日期：2026-01-15")

print("\n季节性航线运营判断：")
print(
    routes.groupby("seasonal")["is_season_available"]
    .agg(["count", "sum"])
)

print("\n当前不可运营的航线数量：")
print((~routes["is_season_available"]).sum())

print("\n当前可运营的航线数量：")
print(routes["is_season_available"].sum())


# 43. 检查地面接驳是否存在反向边

ground_set = set(
    zip(ground["src"], ground["dst"])
)

reverse_count = 0
reverse_pairs = []

for src, dst in ground_set:
    if (dst, src) in ground_set:
        reverse_count += 1
        reverse_pairs.append((src, dst))

print("\n========== 地面接驳方向检查 ==========")

print("地面接驳记录数：", len(ground_set))
print("存在反向连接的方向记录数：", reverse_count)
print("反向连接的机场对样例：", reverse_pairs[:10])


# 44. 检查地面接驳关联的机场运营状态

# 获取关闭机场ID
closed_ids = set(
    airports.loc[
        airports["active"] == 0,
        "airport_id"
    ]
)

# 检查地面接驳起点
ground_closed_src = ground[
    ground["src"].isin(closed_ids)
]

# 检查地面接驳终点
ground_closed_dst = ground[
    ground["dst"].isin(closed_ids)
]

print("\n========== 地面接驳关闭机场检查 ==========")

print("连接关闭机场的起点记录：")
print(ground_closed_src)

print("连接关闭机场的终点记录：")
print(ground_closed_dst)

# 检查od_pairs表
# 45. 检查OD起点和终点是否合法

valid_ids = set(airports["airport_id"])

invalid_od_src = od[
    ~od["src"].isin(valid_ids)
]

invalid_od_dst = od[
    ~od["dst"].isin(valid_ids)
]

print("\n========== OD有效性检查 ==========")

print("OD总数：", len(od))

print("不存在的OD起点记录：", len(invalid_od_src))
print("不存在的OD终点记录：", len(invalid_od_dst))

# 检查是否包含关闭机场
invalid_closed_src = od[
    od["src"].isin(closed_ids)
]

invalid_closed_dst = od[
    od["dst"].isin(closed_ids)
]

print("起点为关闭机场的OD记录：", len(invalid_closed_src))
print("终点为关闭机场的OD记录：", len(invalid_closed_dst))

# 检查起点和终点是否相同
same_od = od[
    od["src"] == od["dst"]
]

print("起终点相同的OD记录：", len(same_od))


# 46. 正式数据清洗：第一步，删除完全重复行

print("\n========== 第一步：删除完全重复行 ==========")

# 保留原始数据，不修改 routes
routes_clean = routes.drop_duplicates().copy()

print("清洗前航线数量：", len(routes))
print("清洗后航线数量：", len(routes_clean))
print("删除的重复记录数：", len(routes) - len(routes_clean))


# 47. 第二步：根据评测日期筛选航线

print("\n========== 第二步：季节性筛选 ==========")

evaluation_month = 1

season_months = {
    "ALL": list(range(1, 13)),
    "DEC-FEB": [12, 1, 2],
    "APR-MAY": [4, 5],
    "JUN-AUG": [6, 7, 8],
    "SEP-OCT": [9, 10]
}

# 判断当前航线是否运营
season_mask = routes_clean["seasonal"].apply(
    lambda x: evaluation_month in season_months.get(x, [])
)

# 保留当前可以运营的航线
routes_clean = routes_clean[season_mask].copy()

print("季节性筛选后航线数量：", len(routes_clean))


# 48. 第三步：删除无效机场连接

print("\n========== 第三步：机场有效性筛选 ==========")

# 获取正常运营机场ID
active_ids = set(
    airports.loc[
        airports["active"] == 1,
        "airport_id"
    ]
)

before = len(routes_clean)

# 起点和终点都必须属于正常运营机场
valid_airport_mask = (
    routes_clean["src"].isin(active_ids) &
    routes_clean["dst"].isin(active_ids)
)

routes_clean = routes_clean[
    valid_airport_mask
].copy()

print("筛选前：", before)
print("筛选后：", len(routes_clean))
print("本步骤删除：", before - len(routes_clean))


# 49. 第四步：检查距离和耗时

print("\n========== 第四步：边权重筛选 ==========")

before = len(routes_clean)

# 距离必须大于0
distance_mask = routes_clean["distance_km"] > 0

# 耗时必须大于0
duration_mask = routes_clean["duration_min"] > 0

# 两个条件必须同时满足
weight_mask = distance_mask & duration_mask

routes_clean = routes_clean[
    weight_mask
].copy()

print("筛选前：", before)
print("筛选后：", len(routes_clean))
print("本步骤删除：", before - len(routes_clean))

print("\n最终距离统计：")
print(routes_clean["distance_km"].describe())

print("\n最终耗时统计：")
print(routes_clean["duration_min"].describe())


# 50. 地面接驳数据清洗

print("\n========== 地面接驳清洗 ==========")

ground_clean = ground.copy()

before = len(ground_clean)

# 删除完全重复记录
ground_clean = ground_clean.drop_duplicates()

# 起点和终点必须正常运营
ground_mask = (
    ground_clean["src"].isin(active_ids) &
    ground_clean["dst"].isin(active_ids)
)

ground_clean = ground_clean[ground_mask].copy()

# 耗时必须大于0
ground_clean = ground_clean[
    ground_clean["duration_min"] > 0
].copy()

# 评测日期的季节性筛选
ground_season_mask = ground_clean["seasonal"].apply(
    lambda x: evaluation_month in season_months.get(x, [])
)

ground_clean = ground_clean[
    ground_season_mask
].copy()

print("清洗前接驳数量：", before)
print("清洗后接驳数量：", len(ground_clean))
print("删除数量：", before - len(ground_clean))


# 51. 清洗结果汇总

print("\n========== 清洗结果汇总 ==========")

print("机场总数：", len(airports))
print("正常运营机场：", len(active_ids))

print("\n航线：")
print("清洗前：", len(routes))
print("清洗后：", len(routes_clean))

print("\n地面接驳：")
print("清洗前：", len(ground))
print("清洗后：", len(ground_clean))

print("\n最终边数：", len(routes_clean) + len(ground_clean))

print("\nOD数量：", len(od))

# 保存清洗后的数据
routes_clean.to_csv(
    "../data/processed/routes_clean.csv",
    index=False,
    encoding="utf-8-sig"
)

ground_clean.to_csv(
    "../data/processed/ground_links_clean.csv",
    index=False,
    encoding="utf-8-sig"
)

print("\n清洗数据已经保存。")


# 52. 审计机场有效性筛选删除的记录

print("\n========== 机场有效性筛选审计 ==========")

# 重新构造去重和季节筛选后的数据
stage2 = routes.drop_duplicates().copy()

season_months = {
    "ALL": list(range(1, 13)),
    "DEC-FEB": [12, 1, 2],
    "APR-MAY": [4, 5],
    "JUN-AUG": [6, 7, 8],
    "SEP-OCT": [9, 10]
}

stage2 = stage2[
    stage2["seasonal"].apply(
        lambda x: 1 in season_months.get(x, [])
    )
].copy()

# 机场ID集合
all_ids = set(airports["airport_id"])

# 关闭机场ID集合
closed_ids = set(
    airports.loc[airports["active"] == 0, "airport_id"]
)

# 不存在的起点、终点
missing_src = ~stage2["src"].isin(all_ids)
missing_dst = ~stage2["dst"].isin(all_ids)

# 连接关闭机场的起点、终点
closed_src = stage2["src"].isin(closed_ids)
closed_dst = stage2["dst"].isin(closed_ids)

# 四类问题分别统计
print("不存在的起点记录：", missing_src.sum())
print("不存在的终点记录：", missing_dst.sum())
print("连接关闭机场的起点记录：", closed_src.sum())
print("连接关闭机场的终点记录：", closed_dst.sum())

# 取四种问题的并集，避免重复计算
invalid_mask = (
    missing_src |
    missing_dst |
    closed_src |
    closed_dst
)

invalid_records = stage2[invalid_mask].copy()

print("\n实际需要删除的不同记录数：", len(invalid_records))

# 查看被删除的记录
print("\n被排除记录：")
print(invalid_records.to_string(index=False))

# 检查负数距离与无效机场是否重叠
negative_distance = stage2["distance_km"] < 0

print("\n季节筛选后负数距离记录数：",
      negative_distance.sum())

print("其中被机场有效性筛选排除的负数距离：",
      (negative_distance & invalid_mask).sum())

print("机场筛选后剩余负数距离：",
      (negative_distance & ~invalid_mask).sum())


# 53. 统计清洗后图的节点和连接

print("\n========== 最终图结构初步统计 ==========")

# 合并航线和地面接驳的起点终点
all_edges = pd.concat([
    routes_clean[["src", "dst"]],
    ground_clean[["src", "dst"]]
], ignore_index=True)

# 统计不同的有向机场对
unique_pairs = all_edges.drop_duplicates(
    subset=["src", "dst"]
)

# 获取正常运营机场
active_airports = airports[
    airports["active"] == 1
].copy()

# 统计所有有边连接的机场
connected_airports = set(all_edges["src"]) | set(all_edges["dst"])

# 找出没有任何边连接的机场
isolated_airports = active_airports[
    ~active_airports["airport_id"].isin(connected_airports)
]

print("正常运营机场数量：", len(active_airports))
print("清洗后边记录数：", len(all_edges))
print("不同有向机场对数量：", len(unique_pairs))
print("有连接的机场数量：", len(connected_airports))
print("孤立机场数量：", len(isolated_airports))

print("\n孤立机场ID：")
print(isolated_airports["airport_id"].tolist())


# 54. 统计机场节点的入度和出度

print("\n========== 机场节点度数分析 ==========")

# 统计每个机场的出度
out_degree = all_edges.groupby("src").size()

# 统计每个机场的入度
in_degree = all_edges.groupby("dst").size()

# 建立机场度数统计表
degree_df = active_airports[["airport_id", "city"]].copy()

degree_df["in_degree"] = (
    degree_df["airport_id"].map(in_degree).fillna(0).astype(int)
)

degree_df["out_degree"] = (
    degree_df["airport_id"].map(out_degree).fillna(0).astype(int)
)

degree_df["total_degree"] = (
    degree_df["in_degree"] + degree_df["out_degree"]
)

print("入度为0的机场数量：",
      (degree_df["in_degree"] == 0).sum())

print("出度为0的机场数量：",
      (degree_df["out_degree"] == 0).sum())

print("总度数为0的机场数量：",
      (degree_df["total_degree"] == 0).sum())

print("\n入度最高的10个机场：")
print(
    degree_df.nlargest(10, "in_degree")
)

print("\n出度最高的10个机场：")
print(
    degree_df.nlargest(10, "out_degree")
)

# 保存节点度数统计
degree_df.to_csv(
    "../results/airport_degree.csv",
    index=False,
    encoding="utf-8-sig"
)


# 55. 检查OD是否涉及孤立机场

isolated_ids = set(
    degree_df.loc[
        degree_df["total_degree"] == 0,
        "airport_id"
    ]
)

# 起点属于孤立机场
od_isolated_src = od[
    od["src"].isin(isolated_ids)
]

# 终点属于孤立机场
od_isolated_dst = od[
    od["dst"].isin(isolated_ids)
]

# 起点或终点至少一个孤立
od_isolated = od[
    od["src"].isin(isolated_ids) |
    od["dst"].isin(isolated_ids)
]

print("\n========== OD孤立机场检查 ==========")

print("200对OD总数：", len(od))
print("起点为孤立机场的OD：", len(od_isolated_src))
print("终点为孤立机场的OD：", len(od_isolated_dst))
print("涉及孤立机场的OD：", len(od_isolated))

print("\n涉及孤立机场的OD详细记录：")
print(od_isolated)

# 56. 补充清洗前后的图结构统计

raw_edges = pd.concat([
    routes[["src", "dst"]],
    ground[["src", "dst"]]
], ignore_index=True)

raw_connected_ids = (
    set(raw_edges["src"]) | set(raw_edges["dst"])
)

raw_isolated = airports[
    ~airports["airport_id"].isin(raw_connected_ids)
]

print("\n========== 清洗前后补充统计 ==========")

print("原始不同有向机场对：",
      len(raw_edges.drop_duplicates()))

print("原始孤立机场数量：", len(raw_isolated))

print("原始孤立机场ID：",
      raw_isolated["airport_id"].tolist())

print("清洗前共享航班记录数：",
      (routes["codeshare"] == 1).sum())

print("清洗后共享航班记录数：",
      (routes_clean["codeshare"] == 1).sum())