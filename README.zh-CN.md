# ppt-reflex · 无需视觉模型，做出正确的 PPT

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Tests](https://img.shields.io/badge/tests-72%20passing-brightgreen.svg)](ppt_reflex/grid/tests/)
[![Version](https://img.shields.io/badge/version-0.6.0-536DFE.svg)](pyproject.toml)
[![Vision-free](https://img.shields.io/badge/vision-free-8e44ad.svg)]()
[![DSH plugin](https://img.shields.io/badge/DSH-dynamic%20plugin-536DFE.svg)]()

**ppt-reflex 是一个让没有视觉能力的 LLM 也能做出 *正确* PPT 的引擎 —— 外加一个 DeepSeek Harness（DSH）插件，提供实时预览与反馈闭环。**

盲 LLM（DeepSeek 优先，但任何纯文本模型都适用）看不到自己生成的 `.pptx`。常见的做法是让模型"猜得更用力"：手写坐标、祈祷渲染正确。ppt-reflex 反其道而行。AI 从不写坐标，也从不猜测视觉效果。它只声明**布局意图**——一个 archetype（布局原语）、一组参数、一个 recipe（组件配方）、一种装饰皮肤——由确定性约束求解引擎算出每一个坐标、量出每一个字形，再用文本把结果反馈回来。

三样东西替代了视觉：

1. **真实字体测量** —— PIL 字形级 FreeType 度量（支持 CJK、遵循 East Asian Width），在渲染*之前*算出文字真正需要的空间。
2. **结构化诊断** —— 每次构建都返回机器可读的问题列表，带 `phase`、`kind`、`severity`、`message`、`options`，AI 可直接执行。
3. **三层 ASCII 反馈** —— L0 结构图、L1 元素图、L2 文本数值表，给模型一张它真正"看得懂"的图。

AI 读诊断、改声明、重跑。`CircuitBreaker`（熔断器）盯着机械式微调，在循环烧死自己之前强制转向设计级方案。

## Agent-Engine 循环

```
            ┌─────────────────────────────────────────────┐
            │                LLM AGENT                    │
            │      （无视觉 —— 读 JSON，不看像素）          │
            │                                             │
            │   ① 声明意图                                │
            │      archetype + params + recipe + skin     │
            │   ② 读诊断 + L0/L1/L2 ASCII                 │
            │   ③ 决定修法 → declare_direction()          │
            └───────────────┬─────────────────▲───────────┘
                            │                 │
              声明          ▼                 │  诊断（JSON）
                            │                 │  + 三层 ASCII
            ┌───────────────▼─────────────────┴───────────┐
            │            引擎（确定性）                     │
            │  解析 archetype → phase1 布局 →              │
            │  碰撞检测 → 构图 → WCAG 对比度 →             │
            │  PIL 文字度量 → 冻结 → 往返校验              │
            │                                             │
            │  CircuitBreaker 守护修复循环                 │
            └───────────────┬─────────────────▲───────────┘
                            │                 │
                  build()   ▼                 │  fix_slide() / rebuild()
                            │                 │
             写出 .pptx —— ok:true = 视觉正确
```

**不是"AI 生成、人来修"，而是"AI 声明、引擎计算、AI 读结果、AI 决策、循环"。** 每个 LLM 都能读 JSON。这就是全部诀窍。
**设计哲学——引擎说 AI 的语言。** 声明层刻意与 HTML/CSS 心智模型同构：这是无视觉模型最深的肌肉记忆。`grid_cards` 读起来像 CSS Grid，`fit_mode` 接受 `contain`/`cover`（对应 `object-fit`），`density` 接受 `comfortable`/`spacious`，`recipe` 像组件 class。**这不是 HTML→PPTX 转换**——没有任何东西从 HTML 渲染；引擎只是借用这套词汇，让盲 LLM 用已有的前端知识驱动布局。映射只存在于一处：`ppt_reflex/grid/agent_vocabulary.py`。

## 特性

- **天生盲 LLM 友好。** AI 不写坐标、不写原始 `python-pptx` 调用。它声明*要什么*——`archetype`、`params`、`recipe`、`frame/rail/corner_mark`——由引擎解出*放哪*。
- **确定性约束求解。** 坐标来自可复现的管线，不来自模型采样。同样的声明 → 同样的布局，每次如此。
- **真实字体测量。** `text_metrics.py` 用 PIL/FreeType 对 Microsoft YaHei（CJK 可用）做字形宽度测量，逐级优雅降级。溢出在写文件*之前*就被捕获，并给出精确的 pt 差值。
- **结构化诊断。** 每条问题 `{slide, phase, kind, severity, message, options}`，去重 + 批量折叠，Agent 读到的是干净清单，不是日志洪流。
- **三层 ASCII 反馈。** `L0` 结构图（区域、皮肤、大色块）· `L1` 元素图（每个元素一个字母，`#` 重叠、`!` 溢出）· `L2` 文本数值表（字号、行数、高度、溢出 pt）。
- **有保障的修复循环。** AI 先声明修法方向（`b.declare_direction("split_slide")`）再重跑。`CircuitBreaker` 逐级升级：同方向两次 → WARN，三次 → BLOCK；三种不同机械微调 → BLOCK；错误数停滞 → "停止微调"。
- **实时可视化（DSH 插件）。** `shell.overlay` 面板逐页预览构建过程，逐元素帧实时推送。可点选元素、拖拽框选、请求改色、反馈问题。
- **两级正确性地板。** `geometry_ok`（零几何错误）与 `harmony_ok`（零美学规则违规）——两者都是可验证的地板，不是品味。天花板是面板前的人。
- **和谐规则，OKLCH 度量。** 60-30-10 面积色彩比、焦点唯一性、色相和谐（单色/邻近/互补/三角）——全部在 OKLCH 度量，阈值集中在 `grid/rules.json`。
- **入口纪律。** `PPTBuilder(strict_tokens=True)`（默认开）以 `raw_color_forbidden` 拒绝裸色与手写坐标；人类面板路径豁免——人是天花板，可以越界（越界导致的对比度问题以 `human_override_warning` 呈现，不阻塞）。
- **审美裁判权在人。** 色盘、hex、预设都是人工资产。引擎只守*客观*底线——WCAG AA 对比度（≥ 4.5:1）与可读性——从不假装自己有品味。
- **设计 token + recipe 是人工资产。** `tokens.json` / `recipes.json` 保存分级数值（间距、圆角、阴影、字号阶梯、颜色）与命名组件（`card`、`kpi`、`quote`）。AI 只引用*层级名*，绝不手写数值；数值由人拥有。

## v0.6.0 新变化

| 变化 | 含义 |
|:--|:--|
| **删除 theme 语义模板层** | 不再有语义模板间接层。`template + style + overrides` 就是全部。 |
| **参数化原语** | `grid_cards` 接受 `columns`（1–4）、`gap`（pt）、`density`（`compact`/`normal`/`airy`）；引擎算网格。 |
| **设计 token + recipe** | `tokens.json` + `recipes.json` + `get_token()` / `resolve_recipe()`；recipe `card`、`kpi`、`quote` 预解析 token 值。 |
| **装饰皮肤** | `frame="top_bottom_band"`、`rail="left"|"right"`、`corner_mark="tl"|"tr"` —— 几何由引擎求解，不手写。 |
| **PIL 真实字体测量** | 字形级 FreeType 宽度替换了 em 估算。 |
| **ASCII 分层反馈** | `L0`/`L1`/`L2` —— 结构、元素、文本数值精度。 |
| **渲染钩子** | `set_render_frame_hook(fn)` 在绘制前逐元素触发 —— 流式预览的桥。 |
| **DSH 插件桥** | `_dsh_ppt_runner.py` —— stdin JSON 进、result JSON 出，附带流式帧与 ASCII。 |

## harmony pass 新变化

| 变化 | 含义 |
|:--|:--|
| OKLCH 色彩核心 | `grid/oklch.py` —— sRGB↔OKLCH、色相距离、chroma/lightness 辅助 |
| 双通道诊断 | violations → `error`/`warning`（阻塞 `ok`）；signals → `advisory`（永不裁剪、永不批量折叠） |
| 面积色彩比 | 60-30-10 容差带按填充面积计；图片经 PIL 主色入账（`image_style_conflict` signal） |
| 焦点唯一性 | 每页有且仅有一个视觉焦点（`focal_point.missing` / `split` / `ambiguous`） |
| 色相和谐 | 单色/邻近/互补/三角，全部 OKLCH 度量；同页高彩度族 ≤2 |
| 入口纪律 | `strict_tokens=True` 默认开；agent 可见 docstring 已重写为无裸色、无手写坐标 |
| CSS 同构词表 | `contain`/`cover`、`comfortable`/`spacious`、`radius` 别名；CSS 幻觉明确拒绝并给替代 |
| 区域诊断 | `inspect_slide(idx, elem_ids)` + `runner --inspect` —— 纯内存，T5 一致 schema |

## 快速开始

### 安装

```bash
git clone <本仓库> && cd <仓库目录>
pip install -e .
```

Python 3.10+。两个运行时依赖：`python-pptx` 与 `Pillow`。

### 最小 deck 示例

```python
from ppt_reflex.builder import PPTBuilder

b = PPTBuilder(template="business", style="corporate_minimal")

b.add_slide("为什么存在",
    archetype="content",
    elements=[
        b.title("python-pptx 是瞎的"),
        b.bullet("文字溢出与隐形文字是无声故障"),
        b.bullet("ppt-reflex 增加了一道渲染前诊断"),
        b.box("每个 LLM 都能读 JSON。\n无需视觉。",
              recipe="card", fill_color=(15, 23, 42)),
    ],
)

result = b.build("output.pptx")
print(result["summary"])
# → "3 issues (0 errors, 3 warnings)"
```

### Runner 命令（DSH stdin-JSON 桥）

```bash
python _dsh_ppt_runner.py < deck_request.json
```

`deck_request.json`：

```json
{
  "action": "build",
  "template": "business",
  "style": "corporate_minimal",
  "output": "output.pptx",
  "slides": [
    {
      "title": "为什么存在",
      "archetype": "content",
      "elements": [
        {"id": "t1", "type": "title", "text": "python-pptx 是瞎的"},
        {"id": "b1", "type": "box", "text": "无需视觉。",
         "recipe": "card", "fill_color": [15, 23, 42]}
      ]
    }
  ]
}
```

### 结果示例

```json
{
  "path": "output.pptx",
  "ok": true,
  "summary": "3 issues (0 errors, 3 warnings)",
  "diagnostics": [
    {
      "slide": 0, "phase": "freeze", "kind": "overflow_vertical",
      "severity": "warning", "elem_id": "e_2",
      "message": "文字需要 44pt，盒子只有 38pt —— 溢出 6pt",
      "options": ["缩小字号", "加宽盒子", "缩短文字"]
    }
  ],
  "ascii": [ { "L0": "…结构图…", "L1": "…元素图…", "L2": [ { "elem_id": "e_2", "font_size": 14, "overflow_pt": 6 } ] } ],
  "survey": { "topic": "…", "template": "business", "questions": "…" }
}
```

`ok: true` 意味着零 *error*、零往返校验失败——文件在视觉上是正确的。warning 是建议性的，由 Agent 决定是否处理。

## DSH 插件工作流

DSH 插件是**host 组合级 Cordis 插件**：它位于 profile 的 bundle 与 patch 层，且同一 profile 由 Web harness 与 DSH Desktop harness 共享——装一份，双端生效。`slideReflex` 服务由 host 层提供；agent 预设（`ppt-maker`）只通过 client Gate 圈定面板显示范围，不再重复挂载插件。

对话流是一个闭环：

```
用户说出需求
        │
        ▼
Agent 问卷（8 项点选）
   主题 / 受众 / 模板 / 风格 /
   内容来源 / 图片 / 页数 / 密度
        │
        ▼
生成 deck（archetype + params + recipe + skin）
        │
        ▼
build ──►  面板预览（shell.overlay），帧实时流式推送
        │
        ▼
反馈闭环
   点选元素 · 拖拽框选 · 改色请求 · 问题反馈
        │
        ▼
fix_slide() / rebuild() ──►  再次预览
```

**面板预览**以 `.pptx` 将使用的同一套 960×540 坐标渲染——同一条确定性管线，两个渲染目标。逐元素帧经 `set_render_frame_hook` 实时推送，你能看着元素一个个落位。

**工作流文件桥**（插件与 Agent 通过 JSON 文件交换状态）：

| 文件 | 用途 |
|:--|:--|
| `_deck_auto.json` | deck 计划（页、archetype、元素） |
| `_frames_auto.jsonl` | 构建帧 —— 面板轮询此文件做预览 |
| `_feedback_auto.json` | 来自面板的用户问题反馈 |
| `_selection_auto.json` | 元素选中（点选 / 框选） |
| `_palette_auto.json` | 改色请求（色盘 / hex 变更） |

## API 概览

| API | 签名 | 用途 |
|:--|:--|:--|
| `PPTBuilder` | `PPTBuilder(template, style, overrides, page_w=960, page_h=540)` | 唯一 AI 入口；模板与风格懒加载 |
| `add_slide` | `add_slide(title, *, archetype, params, regions, elements, arrows, frame, rail, corner_mark)` | 声明一页；archetype 自动把元素路由进区域 |
| `title / subtitle / text / bullet / footer` | `(text, *, style, region)` | 文本原语 |
| `box` | `(text, *, recipe, fill_color, shape_id, …)` | 卡片组件；`recipe` = `card`/`kpi`/`quote` |
| `shape` | `(shape_id, *, fill_color, pw, ph, text, …)` | 20 种形状；形状内文字自动居中 |
| `image` | `(path, *, fit_mode, layout_mode, caption)` | contain-fit；`layout_mode` 或 `auto_layout_mode()` |
| `table` | `(headers, rows, *, region)` | 自动列宽表格，accent 表头行 |
| `divider / arrow` | — | 装饰，永远安全 |
| `build / build_stream` | `(path)` | 一次性构建，或逐页流式生成器 |
| `fix_slide / rebuild` | `(idx, …)` / `(changed_slides, path)` | 原地编辑 + 哈希缓存增量重建 |
| `verify` | `(path)` | 重开 `.pptx`，纯几何结构校验（无需视觉） |
| `declare_direction` | `(direction)` | 向 CircuitBreaker 声明修法策略 |
| `set_render_frame_hook` | `(fn)` | 逐元素回调，用于流式预览 |
| `list_templates / list_style_presets / list_archetypes` | `()` | 供 Agent 浏览的轻量目录 |
| `get_token / resolve_recipe` | `(category, level)` / `(name)` | 设计 token 与 recipe 解析 |

**12 个布局原语：** `title_cover` · `content` · `two_column` · `comparison` · `data_showcase` · `grid_cards` · `image_hero` · `conclusion` · `section` · `quote` · `timeline` · `blank`。

**6 个模板：** `academic` · `business` · `minimal` · `data_report` · `teaching` · `product`。
**6 个风格预设：** `academic_rigorous` · `corporate_minimal` · `tech_dark` · `editorial_magazine` · `creative_vibrant` · `government_solemn`。

## 逃生舱

引擎是地板，不是天花板。当声明不够表达力时，三层逃生舱让 Agent 收回控制权：

1. **手写 regions。** 完全跳过 archetype，直接传显式 `regions=[("name", x, y, w, h, z), …]`。即便纯手工布局，仍享有诊断与修复循环。
2. **元素参数。** 每个原语都接受显式覆盖——`pw`/`ph`、`fill_color`、`corner_radius`、`align_h`、`font_size`。声明式默认，命令式逃生。
3. **Agent 接管代码。** 前两者都不够时，就那一页直接降到原始 `python-pptx`（或 `officecli` skill）。引擎的价值是*循环*，不是锁死你。

## 路线图

- **golden-set 回归（T6）** —— 建立 ≥10 美 + ≥10 丑 deck 基线（各带应过/应拦规则），`make golden` 对 `tests/golden/baseline.json` 输出通过率/拦截率 diff，任一指标下降即失败；`rules.json` 阈值变更必须跑它。
- **从真实反馈蒸馏 golden 素材** —— `_feedback_auto.json` 历史里用户说"丑"=负样本、验收通过的 deck=正样本，由 `tools/golden_harvest.py` 实现。
- **更多 recipe 与 token** —— 扩充人工资产层（`kpi` 变体、数据表 recipe）。
- **更多参数化原语** —— 把 `columns`/`gap`/`density` 式参数带到更多 archetype。
- **参考 PPTX 布局抽取** —— `layout_extractor.py` 已能从现有 deck 推断区域；接入 `register_archetype()`。
- **ASCII → 诊断全联动** —— 让 L1 图中的每个 `#`/`!` 都可点击跳转到对应 JSON 诊断。

---

**ppt-reflex** 采用 MIT 许可证。为 AI Agent 而生。盲防（blind-proof）设计——`ok: true` 意味着文件正确，且无需任何人"看"过它。
