# 风格锚点候选汇总（12 格）

> 状态：**草案，未入库**。来源：21 号落地页生成（landing_pages/21-<domain>-<mood>.html）→ 20 号机械蒸馏（anchors/20-<domain>-<mood>.json）。
> 生成时间：2026-08-16 · 蒸馏方式：脚本按 20 号规则从 HTML 机械提取，未人工补值。

## 12 候选表

| domain×mood | style_ref 建议词 | 气质关键词 | 适用领域 | 主色 OKLCH | scale_ratio | radius 档位 | density 档位 | 主要风险 |
|---|---|---|---|---|---|---|---|---|
| academic×restrained | `quiet-scholar` | 克制 / 严谨 / 学术 | 学术 / 教育 | oklch(0.34 0.035 255) | 1.25 | none | spacious | 系统衬线字体栈在 PPT 端可能缺失，需确认替换字体 |
| academic×editorial | `editorial-paper` | 编辑感 / 注释 / 大字号对比 | 学术 / 出版 / 编辑 | oklch(0.21 0.02 255) | 1.333 | none | spacious | 脚注式信息密度高，PPT 单页承载易超载 |
| academic×friendly | `warm-seminar` | 亲和 / 圆润 / 温暖 | 学术 / 教育 / 培训 | oklch(0.48 0.085 55) | 1.25 | md | comfortable | 圆角 16px 在 PPT 矩形构图下可能需按模板统一 |
| academic×avant-garde | `violet-thesis` | 先锋 / 破格 / 高彩度 | 学术 / 科研前沿 / 展览 | oklch(0.42 0.16 300) | 1.414 | none | comfortable | 破格对齐（负 margin / 错位卡片）依赖相对定位，PPT 栅格需逐页对齐 |
| corporate×restrained | `navy-dossier` | 克制 / 商务 / 稳重 | 商务 / 金融 / 咨询 | oklch(0.35 0.065 255) | 1.25 | none | comfortable | 克制字重差（400）在 PPT 远距离阅读时层级可能不足 |
| corporate×editorial | `report-redline` | 编辑感 / 数据 / 规则线 | 商务 / 咨询 / 数据报告 | oklch(0.32 0.055 258) | 1.333 | none | comfortable | 大标题对比依赖 display 28.43px，PPT 需要更大字号但受 1.333 比值约束 |
| corporate×friendly | `amber-care` | 亲和 / 暖色 / 圆角 | 商务 / HR / 服务 | oklch(0.45 0.055 55) | 1.25 | md | comfortable | 圆角 + 暖色在严肃金融场景可能不合时宜 |
| corporate×avant-garde | `indigo-pitch` | 先锋 / 几何 / 路演 | 商务 / 营销 / 发布会 | oklch(0.38 0.115 275) | 1.414 | sm | compact | 不均匀栅格（2fr 1fr 2fr）与错位卡片迁移到 PPT 需重排 |
| tech×restrained | `console-midnight` | 克制 / 深色 / 高对比 | 科技 / 开发 / 运维 | oklch(0.22 0.035 230) | 1.25 | sm | comfortable | 深色底在投影 / 打印场景需切换浅色皮肤，色彩关系可能变化 |
| tech×editorial | `blueprint-notes` | 编辑感 / 等宽 / 网格 | 科技 / 开发者文档 / 技术报告 | oklch(0.22 0.015 250) | 1.333 | none | comfortable | 等宽字体注释在 PPT 中可能无对应字体 |
| tech×friendly | `soft-byte` | 亲和 / 柔和 / 浅色 | 科技 / 产品 / 社区 | oklch(0.55 0.105 265) | 1.125 | full | comfortable | 1.125 字阶过于平缓，PPT 远距离层级不足 |
| tech×avant-garde | `acid-grid` | 先锋 / 高彩度 / 大字阶 | 科技 / 发布会 / 极客 | oklch(0.34 0.13 295) | 1.414 | none | compact | 酸绿点缀在深底上视觉冲击强，PPT 大面积使用会疲劳 |

## 蒸馏口径说明（20 号规则未定义处，本批次采用的判定）

1. **radius 档位阈值**：0→`none`；1–8px→`sm`；9–20px→`md`；≥21px→`full`（999px 胶囊按钮视为 full）。取卡片与按钮圆角的众数档位。
2. **density 判定**：`(卡片 padding 均值 + card-grid gap) / 2`，≤16→compact；17–32→comfortable；>32→spacious。规范未给加权公式，本批次用简单平均。
3. **scale_ratio**：`display/title` 与 `title/body` 的几何均值，四舍五入到 {1.125, 1.25, 1.333, 1.414} 最近档。
4. **space 三档**：统计页面 margin/padding/gap 中 8px 倍数的出现频次，取前 3 档，按数值大小映射 sm/md/lg。
5. **主辅点缀判定**：按 20 号规则 1——大面积容器（hero 背景、卡片、footer）用 primary/secondary；accent 仅出现在 eyebrow 标签、按钮、卡片 tag、链接 hover 等小元素。
6. **60-30-10 面积比**：为设计意图估计值（bg+primary≈60% / secondary≈30% / accent≈10%），未做像素级统计验证。

## 入库前人工确认清单

1. **style_ref 命名**：12 个 anchor_word 建议词（quiet-scholar / editorial-paper / warm-seminar / violet-thesis / navy-dossier / report-redline / amber-care / indigo-pitch / console-midnight / blueprint-notes / soft-byte / acid-grid）是否被团队命名规范接受。
2. **主色 hue/chroma**：是否需贴合品牌色板微调（如 corporate 藏青 255→品牌蓝）；微调后应重新过一遍蒸馏，避免 JSON 与 HTML 脱节。
3. **scale_ratio 档位**：1.125（tech-friendly）过缓、1.414（avant-garde）过陡是否符合 PPT 可读性；若引擎要求全局统一比值需裁决取舍。
4. **radius / density 判定口径**：上文第 1–2 条的阈值与加权公式为蒸馏器自定，需引擎确认（否则重新蒸馏会得到不同档位）。
5. **space 三档映射**：8px 基间距是否适配引擎 scale 体系（若引擎按 4px 基需换算）。
6. **temperament / domains / skin_compat**：语义是否准确；skin_compat 取值域过宽会导致皮肤混搭失真。
7. **字体栈**：系统衬线 / 等宽字体在 PPT 端需替换为可嵌入字体，替换后字重与字距需复验。
8. **暗色锚点**：tech-restrained / tech-avant-garde 两页依赖深色底，投影与打印环境需双皮肤验证。
9. **破格对齐**：4 个 avant-garde 页依赖负 margin / 错位卡片，入库前确认模板栅格允许。
10. **文案剥离**：各页中文数值（市场规模、工艺参数等）为演示用途示例；锚点只取风格，入库时是否剥离内容字段。
