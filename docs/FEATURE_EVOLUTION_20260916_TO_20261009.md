# VPLINK 地图：2026-09-16 稳定版到 2026-10-09 正式版

| 对比项 | 2026-09-16 稳定正式版（Search v1 开发前） | 2026-10-09 最新正式版 |
|---|---|---|
| 四个入口与品牌隔离 | 已有中立地图、Network Overview、Geekbar、Dojo；品牌专属页按对应 CSV 标记限定点位 | 四个入口和固定范围保留；页面生成进一步改为由品牌配置驱动，**不是**新推出品牌专属地图 |
| 筛选、地图与门店信息 | 已有 States / Categories（读 `StoreType`）/ Brand 筛选、统计、聚类与单点模式、地图样式、门店 Popup 和按 ID 懒加载的 R2 照片 | 这些基础功能保留；增加下述搜索、结果、区域、分享和桌面详情交互 |
| Search 与结果 | 无 Search 输入、联想结果和 `Showing X of Y locations` | 可按门店名、城市、邮编、地址搜索；完整 Location ID 精确命中优先；结果显示 `ID: xxx`；增加范围内数量提示 |
| 桌面与手机 | 地图与原有筛选面板；点击点位查看 Popup | Desktop 地图铺满视口，毛玻璃 Results/Detail 面板覆盖地图；Mobile 仍以地图和 Popup 为主，Search / Filters 可展开 |
| 地图视角与分享 | 无当前版本的结果列表、显式区域搜索和可还原筛选状态的 Share view | Desktop Locations 列表和 Detail、`Search this area` / bbox / `Show all`，以及带筛选、区域、选中 ID 和视角的链接 |
| 运营数据 | 120 个有效唯一点位，21 个 `StoreType`；Geekbar 50、Dojo 60 | 仍为 120 个有效唯一点位；22 个 `StoreType`，Geekbar 50、Dojo 60；变化来自**单独发布的数据更新**，不是地图功能增加 |

## 对比口径

起点是正式版 Git commit [`9d312bede3f94591ad83a06beae196f928971a96`](https://github.com/bds109/vplink-network-map/commit/9d312bede3f94591ad83a06beae196f928971a96)，而非 Search v1 发布之后的某一版。先有 2026-10-03 起的 Preview 开发；Search v1 首次进入 Production 是 2026-10-04 的 [`2943b2bead0619afde7d1591679f8a9c26f24739`](https://github.com/bds109/vplink-network-map/commit/2943b2bead0619afde7d1591679f8a9c26f24739)。后续通过 Preview 验收的 Code/UI 汇总进入 2026-10-09 Production commit [`4799b41b039c778aa758aab9aa0dd11e584da691`](https://github.com/bds109/vplink-network-map/commit/4799b41b039c778aa758aab9aa0dd11e584da691)。最新正式数据随后另行发布；不要把 Preview-only 提交日期当作正式功能上线日期，也不要把中途被否决的白卡片视觉当作当前效果。

## 真正新增的 Code/UI

1. **Search v1（2026-10-04 首次进入 Production）。** 在原有筛选之外加入门店名 `StoreName`、城市 `City`、邮编 `PostalCode` 和地址 `Address` 搜索；归一化大小写、空白与德语重音，例如 `Munchen` 可以匹配 `München`。输入归一化后至少 2 个字符才出现联想结果，中文、英文、德文和数字遵循同一规则。搜索只在当前页面固定品牌范围内进行；增加 `Showing X of Y locations`、手机端 Filters 入口；选择结果时替换冲突的同一筛选维度，保留兼容的筛选。补齐 `柏林州 → Berlin`、`萨克森州 → Sachsen` 映射。以前虽然已有筛选和品牌页，但没有这套搜索与结果计数。
2. **链接状态与发布校验（后续 Preview，随 2026-10-09 Code/UI 推广）。** 可从 URL 恢复/分享州、类别、Overview 品牌筛选、选中门店 ID 及地图中心/缩放；`Share view` 生成当前视图链接。增加构建前 CSV 校验与品牌配置驱动的页面生成：Geekbar / Dojo 两个路由和 Brand 筛选在旧版就存在，新的是生成与校验方式，并非新增品牌或改变 CSV 模式。校验工具属于发布流程，非新的地图按钮。
3. **Desktop Results 与 Area（随 2026-10-09 Code/UI 推广）。** 桌面常驻 Locations 结果列表，支持从列表、地图点位与搜索定位门店。用户拖动/缩放后可按 `Search this area` 将当前地图范围保存为 bbox；区域范围叠加在固定品牌范围及所选筛选条件之上。`Show all` 清除区域限制，不等于取消全部筛选。区域状态可写进分享链接；搜索/直接门店链接可清除区域限制，但不能绕过品牌专属页的范围。
4. **Desktop Detail 与 Mobile Popup（随 2026-10-09 Code/UI 推广）。** 桌面选店在左侧同一个面板内切换为详情，可 Back、Share，并从详情或结果行使用 Directions；选中点在地图上仍清楚可见。手机延用 Popup，不把 Desktop 的 Locations 列表照搬到小屏；在 768 / 769px 切换时保留选中 ID。原版已有 Popup、照片和地图点位；新增的是桌面结果/详情工作流及相关链接操作。
5. **Mobile Search 与 Desktop 视觉（随 2026-10-09 Code/UI 推广）。** 手机搜索输入保持 16px，收展和视口尺寸变化时恢复地图布局。桌面恢复全宽地图，Results/Detail、Stats、Filters 与 Search 使用分层毛玻璃，选中门店自动移到面板无遮挡的地图区域。当前正式视觉是经用户接受的毛玻璃版本，不是已被否决的过渡白卡片方案。
6. **按 Location ID 搜索（随 2026-10-09 Code/UI 推广）。** 在现有 Search 增加 CSV `ID` 的完整精确匹配，优先于名称/城市/邮编/地址匹配；不提供 ID 前缀、部分或模糊匹配。联想结果副信息显示 `ID: <ID>`。原有文字和邮编搜索、品牌隔离、Desktop Detail 和 Mobile Popup 保留。

## 独立的运营数据更新

2026-10-09 的数据更新**不属于**上述 Code/UI 发布。来源是 2026-10-07 原始 XLSX 的 `VPL门店地图信息` 工作表，Preview 数据提交 [`8a47bff19c3bc25a2efe79af6719cab5313ba2df`](https://github.com/bds109/vplink-network-map/commit/8a47bff19c3bc25a2efe79af6719cab5313ba2df)，Production 数据提交 [`d6b4b18479cdf049c49f8cb1a705609e88d64cab`](https://github.com/bds109/vplink-network-map/commit/d6b4b18479cdf049c49f8cb1a705609e88d64cab)。对照起点及上一版数据，120 个有效唯一 ID 未增减；逐字段比较仅 ID 126 的 `StoreType` 从 `Chain Restaurant` 改为 `China Restaurant`，使 `StoreType` 种类由 21 变为 22；Geekbar 50、Dojo 60 不变。当前正式 CSV `VPL门店地图信息.csv` 与 Preview CSV 的 SHA-256 均为 `93b940ad2f84eba438663b89fe49ed267843b2b401638b774039150a8e42387a`。旧版归档与 Git 中旧 CSV 的 SHA-256 为 `b18f1262605d7002cd3352f096b135672191fa65492d70da644863bfe0198bb8`。

使用方式见 [地图使用指南](MAP_USER_GUIDE.md)；逐次正式发布记录见 [CHANGELOG](../CHANGELOG.md)。本页只描述已进入正式版、经源文件和提交核实的变化，不代表新的功能规划。
