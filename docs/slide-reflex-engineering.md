# dsh-slide-reflex + ppt-maker-preset 插件工程维护文档

**最后更新**: 2026年3月22日  
**状态**: 生产可用，活跃维护  
**版本**: 0.1.0

---

## 1. 架构总览

### 组件图

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         DSH 宿主进程 (Node.js)                          │
│  ┌─────────────────────────────────────────────────────────────────────┐│
│  │  SlideReflexGateway (TypertRemoteService)                          ││
│  │  - 构建编排 (build/renderSlides)                                   ││
│  │  - Deck Watcher (fs.watchFile 800ms)                               ││
│  │  - FramesFile RPC (since/epoch 游标)                               ││
│  │  - 反馈闭环 (applyFeedbackBuild)                                   ││
│  │  - ppt_build 工具注册                                              ││
│  └─────────────────────────────────────────────────────────────────────┘│
│                                    │                                    │
│                                    ▼                                    │
│  ┌─────────────────────────────────────────────────────────────────────┐│
│  │  子进程: _dsh_ppt_runner.py (Python)                               ││
│  │  - stdin JSON 接收请求                                             ││
│  │  - ppt_reflex 引擎构建                                             ││
│  │  - stdout JSONL 流式帧输出                                         ││
│  │  - frames_out 原子写入 (os.replace)                                ││
│  └─────────────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                        桥文件 (D:\ppt\)                               │
│  _deck_auto.json       ← Agent 写入 (fs-local/str-replace-editor)     │
│  _frames_auto.jsonl    ← Runner 输出 (原子替换)                        │
│  _feedback_auto.json   ← 面板写入 (颜色/问题请求)                      │
│  _selection_auto.json  ← 面板写入 (选区/元素)                          │
│  _palette_auto.json    ← 面板写入 (配色偏好)                           │
│  _breaker_state.json   ← Runner 读写 (断路器状态)                      │
└─────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                      浏览器面板 (client.js)                             │
│  - 400ms 轮询 framesFile RPC                                         │
│  - Canvas 渲染 (960×540 坐标空间)                                      │
│  - 点击/框选交互                                                       │
│  - 颜色/问题反馈                                                       │
│  - Epoch 重置逻辑                                                      │
│  - i18n (zh/en)                                                        │
└─────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                      预设声明 (ppt-maker-preset)                        │
│  - persona: PPT 制作助手 prompt (141行)                                │
│  - skill: ppt-maker SKILL.md 加载                                      │
│  - filesystem: fs-local (D:\ppt) + str-replace-editor                 │
│  - 无 shell 组 (win32 不支持 terminal inspection)                      │
└─────────────────────────────────────────────────────────────────────────┘
```

### 组件职责一句话

| 组件 | 职责 |
|:--|:--|
| **SlideReflexGateway** | 宿主侧 Typert 服务，管理构建生命周期、deck watcher、帧文件 RPC、反馈闭环 |
| **_dsh_ppt_runner.py** | Python 子进程，执行 ppt_reflex 引擎构建，流式输出帧到 stdout + frames_out |
| **client.js** | 浏览器面板，轮询帧文件、Canvas 渲染、用户交互、反馈写入 |
| **agent.cordis.yml** | 预设声明，定义 Agent persona + 工具组 (skill, filesystem) |
| **桥文件** | 进程间通信通道，UTF-8 JSON/JSONL，原子写入保证一致性 |

---

## 2. 端到端数据流

### 完整流程

```
1. Agent 写入 _deck_auto.json
   ↓
2. Watcher 检测变化 (fs.watchFile 800ms 轮询 + 400ms debounce + content-hash)
   ↓
3. _scheduleWatchBuild() → setTimeout 400ms → _runWatchBuild()
   ↓
4. build() 调用:
   - busy 锁检查 (this.building)
   - 重置 frames[] + lastResult
   - AbortController 超时 (120s)
   - subprocess.spawn({ python, _dsh_ppt_runner.py })
   - stdin: JSON.stringify(req) (含 stream:true, frames_out)
   ↓
5. Runner 执行:
   - 读取 _palette_auto.json 合并 overrides
   - 构建 ppt_reflex 引擎
   - 流式输出: _emit_line({ frame: {...} }) 到 stdout + frames_out tmp
   - 最终输出: _emit_line({ result: {...} })
   - _flush_frames(): os.replace(tmp, frames_out) 原子替换
   ↓
6. 宿主 parseLine() 解析 stdout:
   - { frame } → this.frames.push(frame)
   - { result } → this.lastResult = result
   ↓
7. build() finally:
   - _afterBuild(req): 计算 summarizeDeckChange 摘要
   - this.building = false
   - this.epoch += 1 (构建完成才推进)
   ↓
8. 面板 400ms 轮询 framesFile RPC:
   - 读取 _frames_auto.jsonl
   - 截断检测: fileMax < framesMaxSeen → epoch++ 并重置 since=0
   - 返回 { frames, building, result, epoch }
   ↓
9. 面板渲染:
   - epoch 变化 → 清空 framesBySlideRef，重置 since=0
   - 累积帧到 framesBySlideRef (slide → Map(seq, frame))
   - paint() 渲染当前页到 Canvas (960×540)
   - 更新缩略图
   ↓
10. 用户交互:
   - 点击元素 → setSelElem + saveSelection
   - 框选区域 → setSelArea + saveSelection
   - 添加改色请求 → saveFeedback
   - 添加问题 → saveFeedback
   ↓
11. 反馈闭环:
   - applyAndRebuild() → applyFeedbackBuild()
   - 读取 deck，修改 fill_color
   - writeJson(deckFile) + _markWatchSelfWrite()
   - writeJson(feedbackFile)
   - build() 重新构建
```

### 时序关键点

| 阶段 | 延迟 | 机制 |
|:--|:--|:--|
| Deck 写入 → Watcher 检测 | 800ms + 400ms = 1.2s | fs.watchFile interval + debounce |
| 构建执行 | 0.5~2s | Python 子进程 |
| 帧写入 → 面板可见 | 400ms | 面板轮询间隔 |
| 总延迟 (deck → 面板更新) | ~2~3s | 端到端 |

---

## 3. 文件清单与职责映射表

### 插件源码 (D:\ppt\plugins\dsh-slide-reflex\)

| 文件 | 行数 | 职责 | 关键函数/位置 |
|:--|:--|:--|:--|
| **lib/index.js** | 835 | 宿主端核心: SlideReflexGateway + ppt_build 工具 | L53-61: DEFAULTS 配置; L63-66: 构建常量; L68-81: readJson/writeJson; L147-149: hashText; L244-660: SlideReflexGateway 类; L303-353: _registerDeckWatcher; L355-395: _runWatchBuild; L448-547: build(); L566-600: framesFile RPC; L602-621: applyFeedbackBuild; L669-822: ppt_build 工具注册 |
| **lib/client.js** | 528 | 浏览器面板: 渲染 + 交互 + 反馈 | L1-34: TYPERT_REMOTE; L36-83: I18N; L88-126: paint(); L130-149: Thumb; L151-178: UI 样式; L195-522: Panel 组件; L505-517: Gate 组件 |
| **lib/typert.js** | 54 | 宿主侧 Typert 清单 | L22-53: TYPERT 导出 |
| **lib/remote.js** | 46 | 客户端 Remote 描述符 | L21-45: TYPERT_REMOTE 导出 |
| **package.json** | — | 插件元数据 + dsh 集成声明 | exports, dsh.bundle, dsh.client |
| **cordis.patch.yml** | 10 | 宿主配置补丁 | id: dsh-slide-reflex |
| **README.md** | — | 使用文档 | 安装、配置、工作流、已知限制 |

### 预设 (D:\ppt\plugins\ppt-maker-preset\)

| 文件 | 行数 | 职责 |
|:--|:--|:--|
| **agent.cordis.yml** | 176 | Agent 人格 + 工具组声明 |
| **preset.yml** | 2 | 预设名称描述 |

### 宿主集成

| 文件 | 职责 |
|:--|:--|
| **~/.dsh/profiles/web/package.json** | Bundle 列表 (dsh-slide-reflex link:D:/dsh-plugins/dsh-slide-reflex) |
| **~/.dsh/profiles/web/cordis.patch.yml** | MCP 清单 (filesystem allowed dirs: D:\学术, D:\ppt) |
| **~/.dsh/.agent-presets/ppt-maker/agent.cordis.yml** | 预设副本 (与源同步) |
| **D:/dsh-plugins/dsh-slide-reflex/** | 宿主实际加载目录 (与源同步) |

### 引擎桥接 (D:\ppt\)

| 文件 | 职责 |
|:--|:--|
| **_dsh_ppt_runner.py** | Python 子进程入口，stdin JSON → 引擎 → stdout JSONL |
| **ppt_reflex/live.py** | 遗留组件 (8765 端口实时预览，已弃用，build() 中显式 delete req.live) |

---

## 4. 关键机制详解

### 4.1 Deck Watcher 状态机

**文件**: index.js:303-395

状态字段 (st 对象，构造时初始化):
- lastHash — 上次内容 SHA1 hash
- lastMtime — 上次 stat 的 mtimeMs
- baselineDone — 是否已完成首次基线记录
- timer — debounce setTimeout id
- disposed — 是否已停止

流程:

1. **注册时** (_registerDeckWatcher, L303): 读取 deckFile 初始快照。如果文件已存在 → 设置 lastHash/lastMtime, baselineDone=true；否则 baselineDone=false（等待首次出现）。

2. **watchFile 回调** (onWatch, L322, 每 800ms 轮询): 读取当前快照 (mtime + hash)。mtime 和 hash 都未变 → return。hash 变化 → changed=true。更新 lastMtime/lastHash。如果 !baselineDone → baselineDone=true + 如果 changed → _scheduleWatchBuild()。如果 baselineDone && changed → _scheduleWatchBuild()。

3. **_scheduleWatchBuild** (L355): 清除旧 timer → setTimeout(400ms) → _runWatchBuild() → timer.unref()（不阻止进程退出）。

4. **_runWatchBuild** (L366): 如果 this.building → 排队 (this._pendingWatchBuild = true) 并 return。否则读取 deck → 调用 this.build(deck)。finally: 如果 pendingWatchBuild → 重新调度（补跑机制保证不丢失变更）。

关键设计:
- **Content-hash** 防止 touch-only 变化触发构建 (L326: snap.hash !== st.lastHash)
- **400ms debounce** 合并连续写入
- **pending 补跑** 保证 building 期间的变更不丢失
- **_markWatchSelfWrite** (L400): applyFeedbackBuild 写 deckFile 后更新 watcher baseline，防止自写触发二次构建

### 4.2 build() 生命周期

**文件**: index.js:448-547

```
async build(request):
  1. busy 锁: this.building → return { ok:false, hostError:'busy' }
  2. 初始化: frames=[], lastResult=null, building=true
  3. req 预处理: stream=true, delete req.live, 注入 frames_out
  4. AbortController: setTimeout(120s) → ac.abort()
  5. subprocess.spawn: python _dsh_ppt_runner.py, stdin=req JSON
  6. 流式读取 stdout (增量 readFrom + parseLine)
  7. 进程结束:
     - 如果 stdoutLossy && spillPath → 重解析完整 spill 文件 (L516-522)
     - 返回 { ok, exitCode, result, nFrames, stderrTail }
  8. 超时: proc.terminate() → return { ok:false, hostError:'build timeout' }
  9. finally:
     - clearTimeout(timer)
     - _afterBuild(req) — 计算 summarizeDeckChange 摘要 (L413-417)
     - this.building = false
     - this.epoch += 1 — 构建完成才推进 epoch (L545)
```

关键设计:
- **AbortController** 120s 超时保护 (BUILD_TIMEOUT_MS, index.js:63)
- **stdout spill** 处理大数据量: maxBytes 2MB + spill 16MB (L477)
- **stderr 尾部** 保留最后 600 字符 (L509)
- **epoch 在 finally 推进** 保证构建完成才生效（帧文件已原子替换）
- **delete req.live** (L457): 不再使用 8765 端口遗留 live preview

### 4.3 framesFile 协议

**文件**: index.js:566-600

请求: { since: number }
响应: { ok, hostError, frames, building, result, epoch }

**since 语义**:
- 客户端传递上次读取的最大 seq+1
- 服务端返回 all.slice(since)
- 如果 since > fileMax+1 → 截断到 fileMax+1

**epoch 语义**:
- this.epoch 在 build() finally 中 +=1 (L545)
- **截断检测双保险** (L584-590): fileMax < this.framesMaxSeen → 文件被截断（新构建正在写入） → epoch++ 并重置 from=0
- epoch 变化 → 面板清空帧数据，重置 since=0

**result 叠加** (L595-598):
- 磁盘上的 result 无 summary 字段
- 宿主叠加 this.lastResult.summary（来自 _afterBuild 计算的 summarizeDeckChange）

### 4.4 Typert RPC 信封协议

**文件**: typert.js, remote.js, client.js:19-34

```
客户端 → 服务端:
{
  "type": "client-request",
  "rpcId": "<uuid>",
  "method": "slideReflex/<method>",
  "payload": { "args": { "request": { ... } } }
}

服务端 → 客户端:
{
  "type": "server-response",
  "rpcId": "<uuid>",
  "result": { "ok": true/false, "value": { ... } }
}
```

方法分类 (typert.js:19-20):
- **有参** (parameters: oneArg(), args 中 key 为 request): build, framesFile, applyFeedbackBuild, savePalette, saveFeedback, saveSelection, renderSlides
- **无参** (parameters: []): loadPalette, loadDeck

endpoint 格式: <namespace>/<method> = slideReflex/framesFile 等。

### 4.5 typert.js manifest 结构

**文件**: typert.js:22-53

```
TYPERT = {
  package: 'dsh-slide-reflex',
  face: 'host',
  schemas: [],
  invocations: [{
    id: 'dsh-slide-reflex#slideReflex/<method>',
    service: 'slideReflex', namespace: 'slideReflex', method: '<method>',
    invocation: { kind: 'direct' },
    parameters: oneArg() 或 [],
    result: result(),
    sourceLocation: { file, line, column }
  }, ...],
  model: { services: [], events: [], objects: [] }
}
```

**typert-loader 校验规则** (历史错误 "TYPERT.model must be an object"):
- TYPERT 必须是对象
- TYPERT.model 必须是对象（不可省略，即使为空）
- invocations 每项需有 id/service/namespace/method/parameters/result

### 4.6 面板 client 状态机

**文件**: client.js:195-277

**状态字段**:
- epochRef (useRef(null)) — 当前 epoch，检测构建重置
- sinceRef (useRef(0)) — 下次请求的 since 游标
- framesBySlideRef (useRef(new Map())) — Map<slide, Map<seq, frame>>
- status / statusKind — 显示文本和状态类别 ('wait'|'building'|'done'|'fail'|'loaded')
- viewSlide — 当前查看的页码
- selElem — 选中的元素 ID
- selArea — 框选的矩形区域

**轮询逻辑** (400ms interval, client.js:230-276):

```
1. svc().framesFile({ since: sinceRef.current })
2. if (r.epoch !== epochRef.current):
     → epochRef = r.epoch → 清空 framesBySlideRef → sinceRef = 0 → setTotalSlides(0)
3. 遍历 r.frames:
     sinceRef = (f.seq || 0) + 1
     if (f.clear_slide) → 跳过 (分页标记，building 时切到该页)
     else → 累积到 framesBySlideRef.get(f.slide).set(f.seq, f)
4. 更新状态:
     r.building → 'building'
     r.result.ok → 'done' + summary
     sinceRef===0 → 'wait'
     else → 'loaded'
```

**渲染** (paint(), client.js:88-126):
- 坐标空间 960×540，按 canvas 宽度等比缩放 (s = W/960)
- region: 虚线边框 + 半透明填充
- shape/box: 圆角矩形填充 (arcTo 实现)
- text: 多行文字 (最多 6 行，每行最多 40 字)
- 选中高亮: selElemId 匹配时蓝色 3px 边框
- 框选矩形: dragRect 蓝色虚线 + 半透明填充

**Gate 组件** (client.js:505-517):
- 检查 session.agentPreset === 'ppt-maker'
- 非 ppt-maker 预设 → return null（面板不出现在其他会话中）

### 4.7 ppt_build 工具注册

**文件**: index.js:757-822

注册方式: ctx.tools.register(defineTool({...})) 在 apply() 中调用。

三个 action:

| action | 用途 | 实现 |
|:--|:--|:--|
| build | 显式构建（不依赖 watcher） | gw.build(deck) |
| renderSlides | 渲染每页 PNG 到 _render_vision | gw.renderSlides({ deck }) |
| inspect | 几何诊断（越界/重叠/文本缺失） | inspectDeck(deck, frames, slide, elem_ids) |

**inspectDeck** (index.js:686-736):
- 遍历 deck.slides，对比 frames 中同页元素
- 检测: 超出页面边界 (x < 0 || y < 0 || x+w > pageW || y+h > pageH)
- 检测: 元素两两重叠 (AABB 碰撞)
- 返回: { page, slide_count, slides: [{elements, geometry}], issues, issue_count }

---

## 5. 桥文件字段协议

### _deck_auto.json (Agent → Watcher → Runner)

```json
{
  "action": "build",
  "template": "business",
  "style": "corporate_minimal",
  "page_w": 960,
  "page_h": 540,
  "output": "D:/ppt/ppt_reflex_demo.pptx",
  "stream": true,
  "frames_out": "D:/ppt/_frames_auto.jsonl",
  "slides": [{
    "title": "Demo 封面",
    "archetype": "title_cover",
    "params": { "columns": 2, "density": "normal" },
    "frame": "single",
    "rail": "left",
    "corner_mark": "dot",
    "elements": [
      { "id": "t1", "type": "title", "text": "Demo 演示页" },
      { "id": "b1", "type": "box", "text": "内容", "fill_color": [27, 58, 92], "recipe": "card" }
    ],
    "arrows": [{ "from": "t1", "to": "b1", "text": "flow" }]
  }]
}
```

| 字段 | 类型 | 说明 |
|:--|:--|:--|
| action | string | 固定 "build"（或 "catalog" 获取模板列表） |
| template | string | 布局模板 (business/academic/...) |
| style | string | 样式预设 (corporate_minimal/academic_rigorous/...) |
| page_w/page_h | number | 页面尺寸 (默认 960×540) |
| output | string | 输出 PPTX 路径 (必须在 cwd 内) |
| stream | boolean | true 启用流式帧输出 |
| frames_out | string | 帧文件路径 (宿主自动注入) |
| slides[].archetype | string | 页面版式 (title_cover/grid_cards/two_column/content/timeline/conclusion) |
| slides[].params | object | 布局参数 (columns, density: compact/normal/airy) |
| slides[].frame | string | 页框样式 (single/double/none) |
| slides[].elements[].type | string | 元素类型 (title/subtitle/text/bullet/box/shape/image/table/divider/footer) |
| slides[].elements[].fill_color | [r,g,b] | RGB 数组 0-255 |
| slides[].elements[].recipe | string | 组件类 (card/kpi/quote) |

### _frames_auto.jsonl (Runner → 面板)

每行一个 JSON 对象。三种类型:

**帧对象** (每个元素一行):
```json
{"frame":{"slide":0,"kind":"text","elem_id":"t1","text":"Demo","x":74,"y":74,"w":812,"h":54,"fill":null,"font_size":28}}
```

| 字段 | 类型 | 说明 |
|:--|:--|:--|
| slide | number | 页码 (0-based) |
| kind | string | 元素类型 (text/box/shape/image/region/table/divider) |
| elem_id | string | 元素 ID (与 deck 对应) |
| text | string | 文本内容 |
| x/y/w/h | number | 坐标和尺寸 (960×540 空间，round 1位小数) |
| fill | string/null | 填充色 (#RRGGBB 或 null) |
| font_size | number | 字号 (0 表示无) |

**清除标记** (每页起始):
```json
{"frame":{"clear_slide":true,"slide":0}}
```

**结果对象** (最后一行):
```json
{"result":{"ok":true,"geometry_ok":true,"harmony_ok":true,"build_number":37,"hard_blocked":false,"summary":"本次：结构不变，重新构建","diagnostics":[],"page_summaries":[],"design_hints":[],"template":"business","style":"corporate_minimal"}}
```

| 字段 | 类型 | 说明 |
|:--|:--|:--|
| ok | boolean | 构建是否成功 |
| geometry_ok | boolean | 几何检查通过 (无越界/重叠) |
| harmony_ok | boolean | 和谐检查通过 (色彩/构图) |
| build_number | number | 构建序号 (累加) |
| hard_blocked | boolean | 断路器是否触发阻断 |
| summary | string | 宿主计算的变更摘要 (中文一行) |
| diagnostics | array | 问题诊断列表 [{kind, severity, message}] |
| page_summaries | array | 每页汇总 |
| design_hints | array | 设计建议 |

### _feedback_auto.json (面板 → Agent)

```json
{
  "requests": [
    {"type":"color","slide":0,"elem_id":"b1","color_hex":"#C0392B","label":"说明意图"},
    {"type":"question","slide":0,"elem_id":"t1","question":"太大了","elem_text":"Demo","slide_title":"封面"},
    {"type":"area","slide":0,"area":{"x":100,"y":100,"w":200,"h":150},"elems":["b1"],"question":"太挤","region_elems":[{"id":"b1","text":"内容"}],"slide_title":"封面"}
  ],
  "deck": { ... }
}
```

| 字段 | 说明 |
|:--|:--|
| requests[].type | 'color' (改色) / 'question' (单元素问题) / 'area' (区域问题) |
| requests[].elem_text | 宿主自动内联的元素文本摘要 (buildDeckContext, index.js:420-436) |
| requests[].region_elems | 宿主自动内联的区域元素列表 (id + text) |
| requests[].slide_title | 宿主自动内联的页面标题 |
| deck | applyFeedbackBuild 时附带完整 deck 快照 |

### _selection_auto.json (面板 → Agent)

**单元素选中**:
```json
{"slide":0,"elem_id":"b1","kind":"box","text":"内容","elem_text":"内容·引擎计算","slide_title":"封面"}
```

**框选区域**:
```json
{"slide":0,"area":{"x":100,"y":100,"w":200,"h":150},"elems":["b1","b2"],"region_elems":[{"id":"b1","text":"内容"}],"slide_title":"封面"}
```

### _palette_auto.json (面板 ↔ Runner)

```json
{"accent_hex":"#1D4ED8","bg_hex":"#FFFFFF","swatches":["#1D4ED8","#0F172A","#1B3A5C","#0052D9","#C0392B","#0D9488"]}
```

| 字段 | 说明 |
|:--|:--|
| accent_hex | 主色 (#RRGGBB 或空字符串) |
| bg_hex | 背景色 (#RRGGBB 或空字符串) |
| swatches | 快捷色板数组 |

**合并逻辑** (runner.py:238-261, _merge_palette_overrides):
- 构建前读取 palette 文件，将 accent_hex/bg_hex 合并到 req.overrides
- 显式 overrides 优先，palette 不覆盖
- 文件缺失/损坏时静默跳过
- **这是唯一合并点** — JS 侧不再注入

### _breaker_state.json (Runner 读写)

```json
{
  "decks": {
    "4f53cda18c2baa0c": {
      "fingerprints": {"[4,\"silent_overflow\",\"\"]":{"directions":{"unknown":1},"seen_count":1,"current_level":1}},
      "error_trend":[0,0,0,0,0],
      "build_count":37
    }
  },
  "meta":{"last_fp":"4f53cda18c2baa0c","round":1,"ts":1742668800.0,"cwd":"D:\\ppt"}
}
```

| 字段 | 说明 |
|:--|:--|
| decks | 按 deck 指纹分组的断路器状态 |
| decks[fp].fingerprints | 按错误指纹分组的方向计数器 |
| decks[fp].build_count | 该 deck 的构建次数 |
| decks[fp].error_trend | 最近 5 次构建的错误数趋势 |
| meta.last_fp | 最近一次构建的 deck 指纹 |
| meta.round | 当前修复轮次 |

---

## 6. 配置项清单

### DEFAULTS (index.js:53-61)

| 键 | 默认值 |
|:--|:--|
| python | <python.exe path (host-specific)> |
| cwd | D:\ppt |
| framesFile | D:\ppt\_frames_auto.jsonl |
| deckFile | D:\ppt\_deck_auto.json |
| feedbackFile | D:\ppt\_feedback_auto.json |
| selectionFile | D:\ppt\_selection_auto.json |
| paletteFile | D:\ppt\_palette_auto.json |

### 构建常量 (index.js:63-66)

| 常量 | 值 | 说明 |
|:--|:--|:--|
| BUILD_TIMEOUT_MS | 120000 (120s) | build() 超时保护 |
| WATCH_POLL_MS | 800 | fs.watchFile 轮询间隔 |
| WATCH_DEBOUNCE_MS | 400 | 写入防抖延迟 |
| CONFIG_FILE_KEYS | ['framesFile','deckFile','feedbackFile','selectionFile','paletteFile'] | sanitizeConfig 校验的键 |

### sanitizeConfig 校验规则 (index.js:126-145)

- python: 必须是绝对路径 + 文件存在，否则回退 DEFAULTS
- cwd: 必须是绝对路径 + 目录存在，否则回退 DEFAULTS
- 其他文件键: 必须是绝对路径 + 在 cwd 内 (isPathWithin)，否则回退 DEFAULTS

### cordis.patch.yml 配置覆盖

```yaml
- insert:
    - id: dsh-slide-reflex
      name: dsh-slide-reflex
      config:
        python: 'C:\path\to\python.exe'
        cwd: 'D:\ppt'
        framesFile: 'D:/ppt/_frames_auto.jsonl'
        deckFile: 'D:/ppt/_deck_auto.json'
```

**合并方式** (index.js:266-273): 遍历 ctx.get('loader')?.entries()，找到 id === 'dsh-slide-reflex' 的 entry，取 entry.options.config 与 DEFAULTS 合并。

### runner.py 内置常量

| 常量 | 值 | 说明 |
|:--|:--|:--|
| _BREAKER_STATE | D:\ppt\_breaker_state.json | 断路器状态文件 |
| _LIVE_ALLOWED_PREFIXES | ("http://127.0.0.1:8765",) | live preview URL 白名单 |
| _IMAGE_MAX_BYTES_RUNNER | 50MB | runner 侧图片大小限制 |
| _PALETTE_AUTO | D:\ppt\_palette_auto.json | 面板配色文件 |
| _PALETTE_OVERRIDE_KEYS | ("accent_hex", "bg_hex") | palette 合并的键 |

---

## 7. 部署/升级流程

### 插件部署路径

```
源目录: D:\ppt\plugins\dsh-slide-reflex\
    ↓ (手动同步)
宿主加载目录: D:\dsh-plugins\dsh-slide-reflex\
    ↓ (link: 符号链接)
Profile node_modules: ~/.dsh/profiles/web/node_modules/dsh-slide-reflex
```

**package.json 依赖声明** ($DSH_HOME\profiles\web\package.json):
```json
"dependencies": { "dsh-slide-reflex": "link:D:/dsh-plugins/dsh-slide-reflex" }
```

**bundles 声明** (同文件 dsh.profile.bundles):
```json
"bundles": ["@deepseek-ai/dsh-base", "@deepseek-ai/dsh-web-app", ..., "dsh-slide-reflex"]
```

### 预设部署路径

```
源: D:\ppt\plugins\ppt-maker-preset\agent.cordis.yml
    ↓ (手动复制)
宿主预设: $DSH_HOME\.agent-presets\ppt-maker\agent.cordis.yml
```

### 升级流程

1. **修改源文件** (D:\ppt\plugins\dsh-slide-reflex\)
2. **同步到宿主目录** (D:\dsh-plugins\dsh-slide-reflex\)
3. **重启 DSH 宿主** — **无热重载，必须重启** (package.json dsh.requiresRestart: true)
4. **刷新浏览器页面** — 清除旧面板状态

### 验证清单

```powershell
# 验证源与宿主目录一致性
fc /b "D:\ppt\plugins\dsh-slide-reflex\lib\index.js" "D:\dsh-plugins\dsh-slide-reflex\lib\index.js"

# 验证 node_modules 链接
dir "C:\Users\Lenovo\.dsh\profiles\web\node_modules\dsh-slide-reflex"

# 验证预设副本
fc /b "D:\ppt\plugins\ppt-maker-preset\agent.cordis.yml" "$DSH_HOME\.agent-presets\ppt-maker\agent.cordis.yml"
```

---

## 8. 故障排查手册

### 8.1 面板不更新

| 项目 | 内容 |
|:--|:--|
| **症状** | 写入 deck 后面板无反应，或宿主重启后面板卡在 "等待构建" |
| **根因** | 宿主重启后浏览器缓存旧连接状态；面板轮询 catch 静默吞掉异常 (client.js:274) |
| **修复** | 1. 刷新浏览器页面 (F5)；2. 检查宿主控制台是否有 watch 日志；3. 确认 _frames_auto.jsonl 时间戳是否更新 |
| **代码锚点** | client.js:230-274 (轮询逻辑), index.js:303-353 (watcher 注册) |

### 8.2 TYPERT.model must be an object

| 项目 | 内容 |
|:--|:--|
| **症状** | 宿主启动时报错 "TYPERT.model must be an object"，插件加载失败 |
| **根因** | typert.js manifest 缺少 model 字段 (历史错误，8/16 20:48 已修复) |
| **修复** | 确保 typert.js L48-53 包含 model: { services: [], events: [], objects: [] } |
| **代码锚点** | typert.js:48-53 |

### 8.3 bash terminal inspection unsupported on win32

| 项目 | 内容 |
|:--|:--|
| **症状** | 预设加载时报错 "subprocess-local: terminal inspection is unsupported on platform win32" |
| **根因** | 预设声明了 shell 工具组 (persistent-bash/dsh-terminal-bash/pty)，Windows subprocess 后端不支持 terminal inspection |
| **修复** | 已从 agent.cordis.yml 移除 shell 组，注释说明原因 (L154-159) |
| **代码锚点** | agent.cordis.yml:154-159 |

### 8.4 filesystem 拒绝 D:\ppt

| 项目 | 内容 |
|:--|:--|
| **症状** | Agent 写文件时报错 "file access denied under workspace-write mode" |
| **根因** | 宿主 cordis.patch.yml 的 filesystem MCP allowed dirs 未包含 D:\ppt |
| **修复** | 已在 cordis.patch.yml 添加 D:\ppt: args: ['-y', '@modelcontextprotocol/server-filesystem', 'D:\学术', 'D:\ppt'] |
| **代码锚点** | 宿主 cordis.patch.yml L7-10 |

### 8.5 build 跳号双构建

| 项目 | 内容 |
|:--|:--|
| **症状** | 每次写 deck 触发 2 次构建 (build_number 跳 2) |
| **根因** | 待确认（观察项） |
| **排查方向** | 1. _markWatchSelfWrite (index.js:400) 是否正确更新 watcher baseline；2. applyFeedbackBuild 是否因写 deckFile 触发额外 watcher 回调；3. deck 文件写入是否有瞬间空内容导致 hash 变化两次 |
| **代码锚点** | index.js:397-409 (_markWatchSelfWrite), index.js:602-621 (applyFeedbackBuild) |

### 8.6 日志看不到 watch 记录

| 项目 | 内容 |
|:--|:--|
| **症状** | 想查看 watcher 日志但 dsh-web.log 中没有 |
| **根因** | 插件 logger 输出不进 dsh-web.log（该文件只收 CLI/MCP 子进程输出）；watch 日志走宿主进程 console.log/console.warn |
| **修复** | 查看 DSH Desktop 宿主控制台窗口（Windows Terminal 中的 stdout/stderr） |
| **代码锚点** | index.js:286-296 (_logInfo/_logWarn: 优先用 ctx.logger，回退 console.log) |

---

## 9. 已知坑与维护 TODO

### 已知坑

1. **双构建去重**: 每次写 deck 可能触发 2 次构建（build_number 跳 2），待确认根因
2. **watch 日志不落盘**: 当前只输出到宿主控制台，无法持久化到文件
3. **面板断连无自愈**: 宿主重启后需手动刷新页面，catch 静默吞掉轮询异常 (client.js:274)
4. **str-replace-editor 唯一写文件通道**: Agent 只能通过 str-replace-editor 修改 _deck_auto.json，不能直接 fs write
5. **Unicode 匹配问题**: em-dash (—)、全角字符等在 str-replace 中可能因编码差异匹配失败
6. **编码必须 UTF-8 无 BOM**: PowerShell Get-Content 默认 ANSI 显示乱码，读文件用 [System.IO.File]::ReadAllText(path, [Text.Encoding]::UTF8)
7. **epoch 仅在构建完成推进**: 如果构建超时/崩溃，epoch 不推进，面板可能显示旧帧直到下次成功构建

### 维护 TODO

- [ ] 确认双构建根因并修复（可能是 _markWatchSelfWrite 竞态）
- [ ] 添加 watch 日志落盘机制（写入独立日志文件）
- [ ] 面板断连自动重连提示（轮询失败 N 次后显示"宿主可能已重启，请刷新"）
- [ ] str-replace-editor Unicode 兼容性改进
- [ ] 单元测试覆盖（watcher/framesFile/epoch 状态机）
- [ ] 集成测试（端到端 deck → 面板更新 → 反馈 → 重建）
- [ ] live.py 清理（已弃用，可从 ppt_reflex 中移除或标记 deprecated）

---

## 10. 维护红线

### 必须遵守

1. **代码同步**: 改代码必须同步**源** (D:\ppt\plugins\dsh-slide-reflex\) + **宿主** (D:\dsh-plugins\dsh-slide-reflex\) 两处
2. **重启生效**: 所有插件改动需**重启 DSH 宿主**生效（无热重载，dsh.requiresRestart: true）
3. **文件通道**: 不破坏 str-replace-editor 可写 D:\ppt（这是 Agent 唯一的文件写入通道）
4. **协议同步**: 桥文件协议变更需同步 client.js（面板端解析）与 index.js（宿主端生成）
5. **编码规范**: 所有桥文件/配置 **UTF-8 无 BOM + LF 行尾**

### 禁止操作

- ❌ 不要直接修改宿主 node_modules 中的文件（会被 npm install 覆盖）
- ❌ 不要破坏 watcher 的 content-hash 机制（防止 touch-only mtime 变化触发构建）
- ❌ 不要删除 _breaker_state.json（断路器跨构建持久化状态）
- ❌ 不要在面板端直接写入 deck 文件（必须通过 fs-local / str-replace-editor）
- ❌ 不要在非 ppt-maker 预设中启用面板（Gate 组件做了过滤，但不要绕过）

---

## 附录

### A. 关键代码位置速查索引

| 功能 | 文件:行号 |
|:--|:--|
| DEFAULTS 配置 | index.js:53-61 |
| 构建常量 | index.js:63-66 |
| readJson / writeJson | index.js:68-81 |
| hashText | index.js:147-149 |
| summarizeDeckChange | index.js:166-217 |
| buildDeckContext | index.js:221-242 |
| SlideReflexGateway 构造函数 | index.js:262-284 |
| _registerDeckWatcher | index.js:303-353 |
| _scheduleWatchBuild | index.js:355-364 |
| _runWatchBuild (pending 补跑) | index.js:366-395 |
| _markWatchSelfWrite | index.js:400-409 |
| _afterBuild (摘要) | index.js:413-417 |
| _inlineFeedbackContext | index.js:420-436 |
| parseLine | index.js:438-446 |
| build() 生命周期 | index.js:448-547 |
| renderSlides | index.js:549-564 |
| framesFile RPC | index.js:566-600 |
| applyFeedbackBuild | index.js:602-621 |
| savePalette / loadPalette | index.js:623-630 |
| saveFeedback / saveSelection | index.js:632-650 |
| loadDeck | index.js:652-658 |
| readFramesFile | index.js:669-682 |
| inspectDeck | index.js:686-736 |
| renderToolResult | index.js:738-751 |
| registerPptBuildTool | index.js:757-822 |
| apply() 入口 | index.js:824-835 |
| paint() Canvas 渲染 | client.js:88-126 |
| Thumb 缩略图 | client.js:130-149 |
| UI 样式注入 | client.js:151-178 |
| Panel 组件 (轮询+状态机) | client.js:195-498 |
| Gate 组件 (预设过滤) | client.js:505-517 |
| TYPERT manifest | typert.js:22-53 |
| TYPERT_REMOTE 描述符 | remote.js:21-45 |
| Runner main() | _dsh_ppt_runner.py:407-527 |
| _build_streaming | _dsh_ppt_runner.py:567-618 |
| _emit_line | _dsh_ppt_runner.py:530-542 |
| _merge_palette_overrides | _dsh_ppt_runner.py:238-261 |
| _breaker_before/after_build | _dsh_ppt_runner.py:331-355 |
| _render_pngs | _dsh_ppt_runner.py:359-403 |

### B. 运行时 RPC 探测结果

**探测时间**: 2026-03-22
**端点**: POST http://127.0.0.1:49971/api/slideReflex/framesFile
**结果**: 服务存活，返回结构正确

```json
{
  "type": "server-response",
  "rpcId": "probe-002",
  "result": {
    "ok": true,
    "value": {
      "ok": true,
      "hostError": null,
      "frames": [
        {"clear_slide":true,"slide":0,"seq":0},
        {"slide":0,"kind":"text","elem_id":"t1","text":"Demo","x":74,"y":74,"w":812,"h":54,"fill":null,"font_size":28,"seq":1},
        {"slide":0,"kind":"text","elem_id":"s1","text":"说明意图","x":74,"y":194,"w":812,"h":39,"fill":null,"font_size":18,"seq":2}
      ],
      "building": false,
      "result": {
        "ok": true, "geometry_ok": true, "harmony_ok": true,
        "build_number": 37, "hard_blocked": false,
        "summary": "本次：结构不变，重新构建",
        "template": "business", "style": "corporate_minimal"
      },
      "epoch": 37
    }
  }
}
```

### C. 桥文件当前状态快照

| 文件 | 状态 | 内容摘要 |
|:--|:--|:--|
| _deck_auto.json | ✅ 存在 | business 模板, corporate_minimal 样式, 1 页 demo |
| _frames_auto.jsonl | ✅ 存在 | 3 行 (clear + 2 元素帧), 无 result 行 |
| _feedback_auto.json | ❌ 不存在 | 尚无用户反馈 |
| _selection_auto.json | ✅ 存在 | 上次选区: slide 0 框选区域 |
| _palette_auto.json | ❌ 不存在 | 使用默认色板 |
| _breaker_state.json | ✅ 存在 | build_count=37, deck fingerprint 4f53cda18c2baa0c |

### D. 依赖关系

```
dsh-slide-reflex
├── @deepseek-ai/cordis ^4.0.1 (peer)
├── @deepseek-ai/dsh-typert-protocol * (peer)
├── @deepseek-ai/dsh-tools * (peer)
├── @deepseek-ai/schemastery * (peer)
└── zod * (peer)

ppt-maker-preset
├── @deepseek-ai/dsh-persona
├── @deepseek-ai/dsh-tool-skill
├── @deepseek-ai/dsh-fs-local (cwd: D:\ppt)
└── @deepseek-ai/dsh-tool-str-replace-editor (maxOutputChars: 16000)
```

---

**文档完成** ✓
**覆盖范围**: 插件本体 + 预设声明 + 宿主集成 + 引擎桥接 + 运行时验证
**代码锚点**: 所有机制描述均追溯到具体 file:line
