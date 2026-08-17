# PPT 预览面板深度摸排报告

**排查时间**: 2026-08-17 01:15  
**排查范围**: client.js 全文 + 注入链路 + remotes/RPC 建立 + 运行时探测  
**与 engineering.md 关系**: 互补，聚焦面板侧根因分析，不重复已有内容

---

## 1. 面板组件树 + 打开/渲染状态机

### 1.1 组件树

```
window.__ModuleLoader__.load({ id: "dsh-slide-reflex", factory })
  └── module.exports = { inject: ['timer', 'remote'], async apply(ctx) }
        ├── ensureStyle()              — 注入 CSS 到 <head>
        ├── ctx.remote.$mount(TYPERT_REMOTE)  — 挂载 slideReflex namespace
        ├── svc()                      — 闭包：获取 slideReflex 服务代理
        ├── slots.inject('conversation.input.left', ...)  — 注册到输入栏左侧
        │     └── Gate(props)
        │           ├── useSessions → state.byId[sessionId].agentPreset
        │           ├── if (agentPreset !== 'ppt-maker') return null  ← 关键过滤
        │           └── Panel(props)
        │                 ├── [open, setOpen] = useState(true)  ← 初始值 true
        │                 ├── [status, setStatus] = useState(t.waitBuild)
        │                 ├── [statusKind, setStatusKind] = useState('wait')
        │                 ├── canvasRef (960×540 canvas)
        │                 ├── framesBySlideRef (Map<slide, Map<seq, frame>>)
        │                 ├── sinceRef (游标)
        │                 ├── epochRef (当前 epoch)
        │                 ├── autoOpenedRef (是否已自动打开)
        │                 ├── useEffect([open, viewSlide, selElem, dragRect, lang])
        │                 │     ├── svc().loadPalette() — 加载配色
        │                 │     └── ctx.interval(400ms) — 轮询 framesFile
        │                 │           └── try { svc().framesFile({since}) } catch { /* 静默 */ }
        │                 ├── if (!open) return entryBtn  ← 关闭时只显示入口按钮
        │                 └── return <Fragment>{entryBtn, maskEl, winEl}</Fragment>
        │                       ├── entryBtn: <button class="dsr-entry">PPT</button>
        │                       ├── maskEl: 半透明遮罩 (zIndex: 9999)
        │                       └── winEl: 右侧滑出面板 (zIndex: 10000, 480px宽)
        │                             ├── 标题栏 (状态圆点 + 标题 + 状态文字)
        │                             ├── canvas 画布 (960×540)
        │                             ├── 缩略图栏 (Thumb 组件)
        │                             ├── 改色/问题输入栏
        │                             ├── 反馈请求列表
        │                             ├── 配色面板 (details/summary)
        │                             └── 高级面板 (deck JSON 编辑)
```

### 1.2 打开状态机

#### setOpen 触发路径（全部）

| 触发点 | file:line | 条件 | open 值 |
|:--|:--|:--|:--|
| **初始值** | client.js:196 | `useState(true)` | `true` |
| **auto-open (building)** | client.js:263-266 | `r.building && (epochChanged \|\| (!epochKnown && sinceBefore === 0))` | `true` |
| **✕ 关闭** | client.js:384 | `closePanel = () => { autoOpenedRef.current = true; setOpen(false) }` | `false` |
| **遮罩点击** | client.js:395 | `onClick: closePanel` (同上) | `false` |
| **入口按钮点击** | client.js:388 | `onClick: () => { if (open) autoOpenedRef.current = true; setOpen(!open) }` | toggle |

#### open 持久化

**不持久化**。`useState(true)` 每次组件挂载都是 `true`。组件卸载（会话切换）后状态丢失。

#### 关键行为分析

1. **初始值 `true`** (client.js:196)：Gate 放行后，Panel 立即以 `open=true` 挂载 → 面板**自动展开**（不需要用户点击）
2. **auto-open 仅在 `r.building && epochChanged` 时触发** (client.js:263)：如果面板已被 ✕ 关闭，只有新一轮构建开始时才重新弹出
3. **`autoOpenedRef` 语义**：`false` = 允许 auto-open 弹出；`true` = 已弹出/已手动关闭，不再 auto-open
4. **closePanel 设置 `autoOpenedRef.current = true`** (client.js:384)：用户 ✕ 后，本轮构建期间不再弹出

### 1.3 渲染状态机

#### status/statusKind 触发路径

| 条件 | file:line | status | statusKind |
|:--|:--|:--|:--|
| **初始** | client.js:201-202 | `t.waitBuild` ("等待构建...") | `'wait'` |
| **building** | client.js:268 | `t.building + sinceRef.current + t.elems` | `'building'` |
| **result.ok** | client.js:270 | `t.done + r.result.summary` | `'done'` |
| **result not ok** | client.js:270 | `t.fail` | `'fail'` |
| **sinceRef===0** | client.js:271 | `t.waitBuild` ("等待构建...") | `'wait'` |
| **loaded** | client.js:272 | `t.loaded + sinceRef.current + t.elems` | `'loaded'` |
| **选中元素** | client.js:313 | `t.selectedElem + hit.elem_id + t.canEdit` | (不变) |
| **框选区域** | client.js:326 | `t.boxSelected + elems.length + t.boxSelected2` | (不变) |

#### 关键：sinceRef===0 → "等待构建"

client.js:271: `else if (sinceRef.current === 0) { setStatus(t.waitBuild); setStatusKind('wait') }`

这条路径在以下情况触发：
- `r.frames` 为空数组（没有帧数据）
- `r.building` 为 false（不在构建中）
- `r.result` 为 null（没有构建结果）
- `sinceRef.current` 仍为 0（从未收到过帧）

**这正是当前运行时的状态**：framesFile 返回 `{frames:[], building:false, result:null, epoch:9}`。

### 1.4 画布渲染

#### paint() 全文分析 (client.js:88-126)

```
paint(g, page, selElemId, dragRect, W, H):
  s = W / 960                    ← 缩放因子
  g.clearRect(0, 0, W, H)       ← 清空画布（白色背景）
  for (f of page.values()):     ← 遍历当前页的帧
    if (f.kind === 'region')    ← 区域：虚线边框 + 半透明填充
    if (f.fill)                 ← 形状：圆角矩形填充
    if (f.text)                 ← 文字：多行文字渲染
    if (selElemId === f.elem_id) ← 选中高亮：蓝色边框
  if (dragRect)                 ← 框选矩形：蓝色虚线 + 半透明填充
```

**空白画布的直接原因**：`page` 为空 Map（`framesBySlideRef.current.get(viewSlide) || new Map()`），`g.clearRect` 后没有任何绘制操作 → 白色空白。

---

## 2. 注入挂载链路图

### 2.1 完整链路

```
package.json (dsh-slide-reflex)
  │
  ├── dsh.client.platform: "web"
  ├── dsh.client.inject: ["@deepseek-ai/dsh-api-remotes", "dsh-client-runtime", "dsh-client-connection", "dsh-client-locale"]
  └── exports["./client"]: "./lib/client.js"
        │
        ▼
宿主 ClientModuleLoader (window.__ModuleLoader__)
  │ 加载 client.js → factory(require)
  │
  ▼
client.js factory 执行:
  │ module.exports = { inject: ['timer', 'remote'], async apply(ctx) }
  │
  ▼
宿主 Cordis 实例化:
  │ ctx.remote = ClientRemoteService (dsh-api-gateway:23-29)
  │ ctx.slots = SlotsService (dsh-client-runtime:25-35)
  │ ctx.timer = TimerService
  │
  ▼
apply(ctx) 执行:
  │ 1. ctx.get('slots') — 获取 SlotsService
  │ 2. ensureStyle() — 注入 CSS
  │ 3. ctx.remote.$mount(TYPERT_REMOTE) — 挂载 slideReflex namespace
  │     └── mountContribution → install(descriptor) → installDirect → namespace('slideReflex')
  │           └── RemoteNamespaceService 创建 → 方法代理就绪
  │ 4. slots.inject('conversation.input.left', ...) — 注册 UI 组件
  │
  ▼
UI 渲染 (dsh-client-ui-conversation):
  │ renderSlot("conversation.input.left", zone) (ui-conversation:6873)
  │   → Gate(props) → 检查 agentPreset
  │     → Panel(props) → 面板渲染
  │
  ▼
用户看到:
  │ 非 ppt-maker 会话: 无任何 UI（Gate return null）
  │ ppt-maker 会话:
  │   ├── 初始 open=true → 右侧滑出面板 (480px, zIndex:10000)
  │   └── 用户 ✕ 关闭 → 左侧输入栏内 "PPT" 入口按钮 (class="dsr-entry")
```

### 2.2 面板按钮位置

**入口按钮** (`entryBtn`, client.js:385-391):
- 位置：`conversation.input.left` slot — 输入框左侧工具栏区域
- 样式：`.dsr-entry` — 圆角药丸按钮，48×28px，文字 "PPT"
- 只在面板关闭时显示（client.js:392: `if (!open) return entryBtn`）

**面板窗口** (`winEl`, client.js:398-497):
- 位置：`position: fixed; right: 0; top: 0; height: 100vh; width: 480px`
- 层级：`zIndex: 10000`（最高层）
- 遮罩：`maskEl` 在面板下方，`zIndex: 9999`

### 2.3 Gate 过滤机制

client.js:505-517:
```javascript
function Gate(props) {
  const useSessions = props && props.useSessions
  const sessionId = props && (props.sessionId || (props.session && props.session.sessionId))
  const agentPreset = useSessions
    ? useSessions((state) => {
        if (!state || !state.byId || !sessionId) return undefined
        const summary = state.byId[sessionId]
        return summary ? summary.agentPreset : undefined
      })
    : undefined
  if (agentPreset !== 'ppt-maker') return null
  return React.createElement(Panel, props)
}
```

**关键**：`agentPreset` 必须严格等于 `'ppt-maker'`。如果：
- `useSessions` 不可用 → `agentPreset` 为 `undefined` → return null
- `sessionId` 不可用 → `agentPreset` 为 `undefined` → return null
- 会话不在 `state.byId` 中 → `agentPreset` 为 `undefined` → return null
- `agentPreset` 不是 `'ppt-maker'` → return null

---

## 3. remotes/RPC 建立时序图

### 3.1 正常时序

```
时间轴 →

[T0] 页面加载
  │ window.__ModuleLoader__.load({ id: "dsh-slide-reflex", factory })
  │ factory(require) 执行 → module.exports = { inject, apply }
  │
[T1] Cordis 实例化
  │ ctx.remote = new ClientRemoteService(ctx)  (dsh-api-gateway:23-29)
  │ ctx.slots = new SlotsService(ctx)  (dsh-client-runtime:25-35)
  │
[T2] dsh-api-remotes apply(ctx)
  │ 遍历内置 TYPERT_REMOTE 贡献 (commands, goals, cordis-runner, plugin-inventory, message-feedback)
  │ 每个: ctx.remote.$mount(contribution) → mountContribution → install → namespace
  │
[T3] dsh-slide-reflex apply(ctx)
  │ ctx.remote.$mount(TYPERT_REMOTE)  ← slideReflex namespace 挂载
  │   → mountContribution → validateContribution → install(descriptor)
  │     → namespace('slideReflex') → RemoteNamespaceService 创建
  │     → installDirect(descriptor, token) → namespace.service.installDirect(descriptor)
  │       → 方法代理注册到 namespace.service.direct Map
  │
[T4] svc() 就绪
  │ ctx.remote.namespaces.get('slideReflex').service  ← 可用
  │
[T5] slots.inject('conversation.input.left', ...)
  │ Gate 组件挂载 → Panel 组件挂载
  │
[T6] Panel useEffect 执行
  │ ctx.interval(400ms, async () => {
  │   try {
  │     const r = await svc().framesFile({ since: 0 })
  │     // 处理帧数据...
  │   } catch { /* remote not ready */ }
  │ })
  │
[T7] 第一次轮询
  │ svc().framesFile({ since: 0 })
  │ → RemoteNamespaceService.direct.framesFile({ since: 0 })
  │ → invokeMethod → WebSocket RPC → 宿主 framesFile()
  │ → 返回 { frames, building, result, epoch }
```

### 3.2 竞态窗口分析

**窗口 A: 面板先于 namespace 挂载就绪**

如果 Panel 组件在 `$mount(TYPERT_REMOTE)` 完成前就挂载并开始轮询：
- `svc()` 调用 `ctx.remote.namespaces?.get('slideReflex')?.service`
- 如果 namespace 尚未就绪 → `service` 为 `undefined` → 抛出 `'slideReflex remote namespace is not mounted'`
- **被 catch 静默吞掉** (client.js:274: `catch { /* remote not ready */ }`)
- **下一次 400ms 后重试** → 如果此时 namespace 已就绪，则恢复正常

**结论**：这是一个**瞬态竞态**，不是永久性问题。400ms 后重试会成功。

**窗口 B: 宿主重启后不刷新页面**

宿主重启后：
1. WebSocket 断开
2. `dsh-client-connection` 检测到断连
3. 自动重连逻辑（需确认是否自动重连）
4. 重连后，`ctx.remote` 的 namespace 映射是否自动重建？

**关键问题**：`ctx.remote.namespaces` 是客户端内存中的 Map。宿主重启后：
- 客户端的 `RemoteNamespaceService` 实例仍在内存中
- 但宿主侧的 `SlideReflexGateway` 实例已重建
- WebSocket 重连后，RPC 代理是否能正确路由到新宿主实例？

**需要用户侧验证**：宿主重启后，不刷新页面，面板是否能恢复轮询。

### 3.3 svc() 抛错被吞的永久性场景

client.js:189-193:
```javascript
const svc = () => {
  const s = ctx.remote.namespaces?.get(SERVICE)?.service
  if (s === void 0) throw new Error('slideReflex remote namespace is not mounted')
  return s
}
```

client.js:230-274:
```javascript
const iv = ctx.interval(async () => {
  try {
    const r = await svc().framesFile({ since: sinceBefore })
    // ...
  } catch { /* remote not ready */ }
}, 400)
```

**如果 `$mount` 从未成功**（例如 typert manifest 校验失败、WebSocket 连接失败）：
- `ctx.remote.namespaces` 中永远没有 `'slideReflex'` 条目
- `svc()` 每次都抛错
- catch 静默吞掉
- **轮询永远失败，面板永远空白**

**但**：`$mount` 在 `apply(ctx)` 中被 `await`（client.js:186），如果失败会抛出异常，整个 `apply` 失败，面板不会挂载。所以 `$mount` 成功是面板挂载的前提。

**真正的问题场景**：`$mount` 成功后，宿主重启 → namespace 映射可能失效 → svc() 抛错被吞 → 永久空白。

---

## 4. "面板空白"根因判定表

### 4.1 当前运行时状态（实测确认）

| 项目 | 值 | 证据 |
|:--|:--|:--|
| 宿主端口 | 50079 | 实测 |
| client.js rev | c34a60cbc908 | SHA1 匹配 |
| framesFile epoch | 9 | RPC 探测 |
| framesFile 帧数 | 0 | RPC 探测 (since=0 → frames:[]) |
| framesFile building | false | RPC 探测 |
| framesFile result | null | RPC 探测 |
| _frames_auto.jsonl 大小 | 0 bytes | 文件系统 |
| _frames_auto.jsonl 最后写入 | 01:01:26 | 文件系统 |
| _deck_auto.json | 存在，有内容 | 文件系统 |
| breaker build_count | 40 | _breaker_state.json |
| breaker last_fp | 4f53cda18c2baa0c | _breaker_state.json |

### 4.2 根因判定表

#### 根因 A: 帧文件为空 → 画布空白（**已确认，当前根因**）

| 项目 | 详情 |
|:--|:--|
| **触发条件** | `_frames_auto.jsonl` 为 0 字节 |
| **代码证据** | index.js:570-578: `readFileSync(framesFile, 'utf-8').split('\n')` → 空字符串 → 无 JSON 行 → `all = []` |
| **面板表现** | `frames: [], building: false, result: null` → client.js:271: `sinceRef.current === 0` → `setStatus(t.waitBuild)` → "等待构建（在对话里说需求，助手自动生成）" |
| **画布表现** | `framesBySlideRef` 为空 Map → `paint()` 只做 `clearRect` → 白色空白 |
| **实测证据** | RPC `framesFile({since:0})` 返回 `frames:[]`；文件 0 bytes |
| **如何排除** | 触发一次新构建（在 ppt-maker 会话中说需求），观察 framesFile 是否有内容 |

#### 根因 B: 面板未打开（Gate 过滤）

| 项目 | 详情 |
|:--|:--|
| **触发条件** | 当前会话的 `agentPreset` 不是 `'ppt-maker'` |
| **代码证据** | client.js:515: `if (agentPreset !== 'ppt-maker') return null` |
| **面板表现** | 完全不渲染，连 "PPT" 按钮都看不到 |
| **如何排除** | 确认用户在 ppt-maker 预设会话中 |

#### 根因 C: svc() 抛错被 catch 吞掉 → 轮询永不成功

| 项目 | 详情 |
|:--|:--|
| **触发条件** | `ctx.remote.namespaces` 中没有 `'slideReflex'` 条目 |
| **代码证据** | client.js:190-191: `if (s === void 0) throw new Error(...)` ; client.js:274: `catch { /* remote not ready */ }` |
| **面板表现** | 面板打开，标题栏显示 "等待构建"，画布永远空白，状态永远不更新 |
| **触发场景** | 宿主重启后不刷新页面 → namespace 映射失效 |
| **如何排除** | 刷新浏览器页面（F5）后观察是否恢复 |

#### 根因 D: epoch/since 游标问题

| 项目 | 详情 |
|:--|:--|
| **触发条件** | `sinceRef.current` 已经超过帧文件中的最大 seq |
| **代码证据** | index.js:592: `if (from > fileMax + 1) from = fileMax + 1` → 返回空 frames |
| **面板表现** | 面板显示 "已加载 N 个元素"，但画布可能显示旧帧或空白 |
| **当前状态** | 不适用——framesFile 本身就为空，since=0 也返回空 |

#### 根因 E: 帧渲染失败（paint 异常）

| 项目 | 详情 |
|:--|:--|
| **触发条件** | `paint()` 抛出异常（例如 canvas context 获取失败） |
| **代码证据** | client.js:226-228: `if (!cv) return` + `paint(...)` — 无 try-catch |
| **面板表现** | 面板打开，标题栏可能有状态更新，但画布空白 |
| **当前状态** | 不适用——根本就没有帧数据传入 paint() |

### 4.3 根因优先级排序

1. **根因 A（帧文件为空）** ⭐⭐⭐ — **当前实测确认的直接原因**
2. **根因 C（namespace 失效）** ⭐⭐ — 宿主重启后可能触发，需用户侧验证
3. **根因 B（Gate 过滤）** ⭐ — 需确认用户是否在正确会话中
4. **根因 D/E** — 当前不适用

---

## 5. 用户侧验证清单

### 5.1 基础验证

| # | 操作 | 预期现象 | 对应根因分支 |
|:--|:--|:--|:--|
| V1 | 确认当前会话是 ppt-maker 预设 | 输入框左侧应有 "PPT" 药丸按钮 | B: 看不到按钮 = Gate 过滤 |
| V2 | 如果有 "PPT" 按钮，点击它 | 右侧滑出 480px 面板 | B: 按钮存在 = Gate 通过 |
| V3 | 观察面板标题栏状态文字 | 应显示 "等待构建..." 或 "构建中..." | A: "等待构建" = 帧文件为空 |
| V4 | 观察面板标题栏圆点颜色 | 灰色=等待, 黄色=构建中, 绿色=完成, 红色=失败 | A: 灰色 = 无帧数据 |

### 5.2 恢复验证

| # | 操作 | 预期现象 | 对应根因分支 |
|:--|:--|:--|:--|
| V5 | 在 ppt-maker 会话中说 "帮我做一页 PPT" | 面板状态变为 "构建中..."，画布出现内容 | A: 恢复 = 帧文件被新构建写入 |
| V6 | 如果 V5 无反应，按 F5 刷新页面 | 面板重新挂载，轮询重新开始 | C: 刷新后恢复 = namespace 失效 |
| V7 | 如果刷新后仍无反应，重启 DSH 桌面端 | 完全重新加载 | C: 重启后恢复 = 宿主侧问题 |

### 5.3 深度验证

| # | 操作 | 预期现象 | 对应根因分支 |
|:--|:--|:--|:--|
| V8 | 打开浏览器 DevTools → Console | 搜索 "slideReflex" 或 "remote namespace" | C: 有报错 = namespace 问题 |
| V9 | 打开浏览器 DevTools → Network → WS | 检查 WebSocket 连接状态 | C: 断开 = 连接问题 |
| V10 | 在 Console 执行 `document.querySelector('.dsr-entry')` | 返回按钮元素或 null | B: null = Gate 过滤 |

---

## 6. 修复建议

### 6.1 针对根因 A: 帧文件为空

**问题**：最后一次构建（build #40）写入了空的帧文件。

**可能原因**：
- Python runner 崩溃/异常退出，`_flush_frames()` 未执行，但 `_emit_line` 的 tmp 文件被清理
- Runner 的 `_build_streaming()` 返回前 frames 列表为空
- `os.replace(tmp, frames_out)` 替换了一个空 tmp 文件

**修复建议**：

1. **最小改动：framesFile RPC 增加空帧保护** (index.js:599)
   ```javascript
   // 当前：return { ok: true, hostError: null, frames: all.slice(from), building: result === null && all.length > 0, result: resultOut, epoch }
   // 建议：当 frames 为空且 result 为 null 时，返回 lastKnownFrames（内存缓存）
   ```
   - 位置：index.js:599
   - 改动：在 `build()` 中缓存上一次成功的 frames，在 `framesFile()` 中当磁盘帧为空时返回缓存

2. **根治：Runner 原子写入保护** (_dsh_ppt_runner.py)
   - 确保 `_flush_frames()` 只在 frames 非空时才 `os.replace`
   - 如果 frames 为空但 result 有错误，写入一行 result 而不是空文件

### 6.2 针对根因 C: namespace 失效

**问题**：宿主重启后，客户端的 `ctx.remote.namespaces` 中 `slideReflex` 条目可能失效。

**修复建议**：

1. **轮询增加重试提示** (client.js:274)
   ```javascript
   // 当前：catch { /* remote not ready */ }
   // 建议：catch (e) { 
   //   failCount++
   //   if (failCount > 15) { setStatus('连接可能已断开，请刷新页面'); setStatusKind('fail') }
   // }
   ```
   - 位置：client.js:274
   - 改动：增加连续失败计数器，超过阈值（如 15 次 = 6 秒）后显示提示

2. **namespace 自动重连** (dsh-api-gateway 或 dsh-client-connection)
   - 需要宿主 SDK 层面支持：WebSocket 重连后自动重新广播 namespace manifest
   - 这是 SDK 层面的改动，非插件层面

### 6.3 针对根因 B: Gate 过滤

**当前设计是正确的**：非 ppt-maker 会话不应显示面板。无需修复。

**但可以改进**：如果用户在非 ppt-maker 会话中期望看到面板，可以在入口按钮处显示 tooltip 提示 "仅在 PPT Maker 会话中可用"。

### 6.4 最小改动优先级

| 优先级 | 改动 | 文件:行 | 影响 |
|:--|:--|:--|:--|
| P0 | 帧文件为空保护 | index.js:599 | 防止空白面板 |
| P1 | 轮询失败提示 | client.js:274 | 用户知道需要刷新 |
| P2 | Runner 空帧保护 | _dsh_ppt_runner.py | 根治空帧文件 |
| P3 | namespace 重连 | SDK 层面 | 长期方案 |

---

## 附录

### A. 关键代码位置速查

| 功能 | file:line |
|:--|:--|
| 初始 open=true | client.js:196 |
| auto-open 条件 | client.js:263-266 |
| ✕ 关闭 | client.js:384 |
| 入口按钮 toggle | client.js:388 |
| Gate agentPreset 过滤 | client.js:515 |
| svc() 实现 | client.js:189-193 |
| svc() 抛错被 catch | client.js:274 |
| 轮询 400ms | client.js:230-275 |
| useEffect 依赖数组 | client.js:277 |
| paint() 渲染 | client.js:88-126 |
| "等待构建" 触发 | client.js:271 |
| framesFile 读取 | index.js:566-600 |
| epoch 推进 | index.js:545 |
| $mount 实现 | dsh-api-gateway:35-44 |
| namespace 创建 | dsh-api-gateway:188-200 |
| conversation.input.left 渲染 | ui-conversation:6873 |

### B. 运行时探测结果汇总

| 探测 | 结果 |
|:--|:--|
| GET client.js?rev=c34a60cbc908 | 200, 35207 bytes, SHA256 匹配 |
| POST framesFile {since:0} | epoch=9, frames=[], building=false, result=null |
| POST framesFile {since:3} | epoch=9, frames=[], building=false, result=null |
| POST loadPalette | ok=true, palette={accent_hex:'',bg_hex:'',swatches:[]} |
| POST loadDeck | ok=true, deck 存在 |
| _frames_auto.jsonl | 0 bytes, 最后写入 01:01:26 |
| _deck_auto.json | 存在，business 模板, 1 页 demo |
| _breaker_state.json | build_count=40, deck fingerprint 4f53cda18c2baa0c |

### C. 需用户侧观察项

| # | 观察项 | 对应根因分支 | 如何观察 |
|:--|:--|:--|:--|
| U1 | ppt-maker 会话中是否有 "PPT" 按钮 | B | 看输入框左侧 |
| U2 | 点击 "PPT" 后面板是否滑出 | B | 右侧 480px 面板 |
| U3 | 面板标题栏状态文字 | A/C | "等待构建" / "连接断开" |
| U4 | 面板画布是否有内容 | A | 白色空白 vs 有元素 |
| U5 | 触发新构建后面板是否更新 | A | 说 "做一页 PPT" 后观察 |
| U6 | 刷新页面后面板是否恢复 | C | F5 后观察 |
| U7 | 浏览器 Console 是否有报错 | C | DevTools → Console |
