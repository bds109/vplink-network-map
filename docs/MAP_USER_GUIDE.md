# VPLINK 地图使用指南（2026-10-09 正式版）

## 选择地图入口

| 入口 | 用途与范围 |
|---|---|
| [中立地图](https://map.vplink-automaten.de/) | 显示当前有效点位，不提供 Overview 的品牌选择器。 |
| [Network Overview](https://map.vplink-automaten.de/network-overview/) | 显示当前有效点位，可在 Brand 中选择 Geekbar、Dojo；未选择时显示全部点位。 |
| [Geekbar](https://map.vplink-automaten.de/geekbar/) | 固定只显示 CSV 中 Geekbar 标记为 `1` 的点位。 |
| [Dojo](https://map.vplink-automaten.de/dojo/) | 固定只显示 CSV 中 Dojo 标记为 `1` 的点位。 |

品牌专属页的范围不可通过 Search、筛选、分享链接或直接 `id` 链接绕过。同一门店可以同时属于两个品牌；当前数据总计 120 个有效唯一点位，其中 Geekbar 50、Dojo 60。数据与地图功能分别发布，点位数量会随获批数据更新变化。

## 搜索门店

> 搜索提示：请至少输入 2 个字符后查看联想结果（中文、英文、德文及数字均适用）。例如可输入“酒家”或“Berlin”；只输入“酒”或“帝”等单个字符不会显示建议。可搜索门店名称、城市、邮编和地址，也可输入完整的 Location ID 精确查找。品牌专属地图仅显示相应品牌点位。

- Search 匹配 CSV 的 `StoreName`、`City`、`PostalCode`、`Address`；忽略大小写、首尾/连续空白，并对部分重音作归一化，例如 `Munchen` 可匹配 `München`。目前**不**索引 `CityCN`，也不支持拼音或语义搜索。输入 `a` 或任意单个字符不会出现建议；这不是无结果提示。
- 输入完整 CSV `ID` 时，精确匹配的门店排在其他文字或数字命中之前；不支持只输入 ID 的一部分进行 ID 匹配。ID 也必须满足 Search 的至少 2 字符触发条件。结果显示门店名和 `ID: xxx`、邮编/城市、地址；建议最多显示前 10 条，若匹配更多会显示总数提示。
- Search 的候选范围取决于所打开的地图入口，不会跨页检索其他品牌。选择结果会自动调整冲突的州、类别或 Overview 品牌筛选以显示该门店，同时保留兼容条件；区域搜索范围会被清除，但品牌专属页的固定范围不变。
- Desktop 选择搜索建议后在左侧打开 Detail，地图把选中点移到面板无遮挡区域；Mobile 打开该点的 Popup。移动端地图刚初始化、聚类点尚未就绪时立即点建议，偶尔可能只更新链接而未弹出 Popup；稍等地图载入后重试。这个已知时序问题尚未单独修复。

## 筛选、计数与地图

- **States** 按标准州名筛选；**Categories** 的值来自 CSV `StoreType`，不是 `Category`；Network Overview 的 **Brand** 可选 Geekbar / Dojo。一个筛选维度内多选按“任一”匹配，不同维度之间共同限制结果；`Clear` 清对应维度，`Clear filters` 清可选筛选，不会解除品牌专属页的固定范围。
- `Showing X of Y locations`：Y 是当前页面固定业务范围内的有效点位数，X 是应用当前筛选和已启用区域范围后的显示数。Stats 随当前显示结果更新；如果新 `StoreType` 出现在 CSV 中，会进入 Categories 而非被隐藏。
- 地图默认底图为 OpenStreetMap。可手动切换 OSM、Carto Light、Carto Dark、带标签的卫星图和 Amap；可使用地图缩放、重置视角及聚类/单点切换。门店 Popup 可以查看基本资料与已有照片；照片按 CSV `ID` 在 R2 延迟查找，不在地图初次载入时逐店加载。没有首张照片时不会显示破图区域。

## Desktop：Results、Detail 与区域

- 屏宽 **大于 768px** 时，毛玻璃左侧面板覆盖在全宽地图上。Results 内的 Locations 列表可选门店；从地图点位或 Search 选中也会进入同一面板的 Detail。`Back to locations` 返回列表并清除当前选中门店，保留其他筛选/区域状态。详情可用 **Share** 复制链接，用 **Directions** 按坐标打开 Google Maps 路线；结果列表也提供 Directions 链接。
- 拖动、主动缩放或点聚类后，可出现 `Search this area`。只有点击它，当前可见地图范围才被保存为区域（URL 中的 `bbox`）并用于过滤；只是移动地图不会立即重算区域结果。区域限制叠加在当前页面品牌范围及州/类别/品牌筛选上。`Show all` 清除的是区域限制，不自动清空这些筛选；详情中的 `Show all` 也保留选中的门店。
- 面板可收起再展开；选中门店的标记会尽量留在无遮挡的地图区域。不要把仅移动地图造成的视角变化误认为已启用区域搜索。

## Mobile 与分享

- 屏宽 **768px 及以下**时，地图优先显示，Search 和 Filters 从顶部控件展开；Mobile 不提供 Desktop 常驻 Locations 列表与侧栏 Detail。点选位置后查看 Popup，关闭 Popup 会清除该选中 ID。切换屏宽时，已选中的合法门店可在 Mobile Popup 与 Desktop Detail 之间恢复。
- **Share view** 保存当前有效筛选、区域 `bbox`、选中 `id` 与地图中心/缩放信息，生成可复制的 URL；移动端在浏览器支持时可使用系统分享，失败时尝试复制链接。链接打开后仍受该页面的固定品牌范围限制。地图链接是对当前视图的描述，不是数据快照；日后 CSV 变化，结果也可能变化。
- 门店详情/Popup 的 **Directions** 用门店 CSV 坐标打开 Google Maps 路线。图片仍按 `ID-01.jpg`、`ID-02.jpg` 等顺序发现，图片数量依门店而异。

本指南对应正式 Code/UI 提交 `4799b41b039c778aa758aab9aa0dd11e584da691` 和随后独立发布的数据提交 `d6b4b18479cdf049c49f8cb1a705609e88d64cab`。版本前后对比见 [功能演进](FEATURE_EVOLUTION_20260916_TO_20261009.md)，正式发布记录见 [CHANGELOG](../CHANGELOG.md)。
