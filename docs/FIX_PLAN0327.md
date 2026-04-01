# 位移台多次移动后崩溃修复计划（2026-03-27）

目标：定位并修复“位移台连续多次移动后触发 access violation 崩溃”的根因。

---

## 第一步：建立可复现与证据链（先定位，不盲改）
- [ ] 固化复现路径
    - [ ] 统一测试动作：XUP 连续 30 次、YUP 连续 30 次、ZUP 连续 30 次。
    - [ ] 每次测试记录环境：相机 ON/OFF、DO ON/OFF、速度参数、步长参数。
- [ ] 增强日志（语句级）
    - [ ] 为 Move/StepMove 的关键调用加 BEFORE/AFTER breadcrumb：
        - add_do_chan
        - cfg_samp_clk_timing
        - write
        - start
        - wait_until_done
        - stop
    - [x] 新建并统一写入 `crash_breadcrumb.log`，确保每条日志 flush。
- [ ] 崩溃证据归档
    - [ ] 崩溃后保存 `crash_dump.log` + `crash_breadcrumb.log` + 当次参数快照。

交付物：
- 一份“最后成功调用点”定位结论（精确到语句级）。

---

## 第二步：做隔离测试（缩小问题范围）
- [ ] A 组：Camera OFF + DO ON（仅测位移台）
- [ ] B 组：Camera ON + DO OFF（仅测相机）
- [ ] C 组：Camera ON + DO ON（联合场景）
- [ ] D 组：Camera OFF + DO OFF（基线）

判定规则：
- 仅 A 崩：位移台/DO 路径主因。
- 仅 C 崩：并发或资源竞争主因。
- A/B 都崩：环境或线程共因。

交付物：
- A/B/C/D 结果矩阵 + 初步归因。

---

## 第三步：最小修复（按风险优先级）
### 3.1 线程安全修复（高优先级）
- [x] 检查并消除 DO 工作线程对 UI 控件的直接 `setValue`。
- [ ] 所有 UI 更新通过 Qt signal/slot 切回主线程。

### 3.2 Move/StepMove 时序修复（高优先级）
- [x] `StepMove` 内先计算目标值 `target`。
- [x] `Move` 支持显式参数 `target_pos`，优先使用该值计算 `distance`。
- [ ] 运动完成后同步 `current/position` 到同一目标，避免下一次读旧值。

### 3.3 参数硬约束（中优先级）
- [x] speed > 0
- [x] samps_per_chan > 0
- [x] rate 在设备允许区间内
- [x] 非法参数直接中止下发，记录 `DO_PARAM_INVALID`。

交付物：
- 最小代码变更清单（仅涉及 ThreadDO 相关路径）。

---

## 第四步：稳定性验证（修复后必须跑）
- [ ] 短测：A 组连续点击 100 次，不崩溃。
- [ ] 压测：A 组运行 20 分钟，不崩溃。
- [ ] 联测：C 组（相机+位移台）运行 20 分钟，不崩溃。
- [ ] 结果归档：保存当次日志和参数快照。

验收标准：
- [ ] 连续测试期间无 access violation。
- [ ] 不出现“点两下才动一下”或随机丢步。
- [ ] 崩溃日志为空或仅有历史记录。

---

## 第五步：回退与应急策略（防止卡住）
- [ ] 若修复后出现新回归，按单项变更逐一回退并复测。
- [ ] 保留最后一个稳定版本标签，确保可快速切换。
- [ ] 若仍无法稳定，临时启用“保守模式”（降低速度/步长）。

---

## 执行约束
- 先定位，后修复；每次只改最小范围。
- 每次改动后必须做至少一轮 A 组回归测试。
- 未验证通过前，不合并额外功能改动。

---

## 本轮已执行（代码侧）
- `Generaic_functions.py`：新增 `parse_debug_flag` 与 `write_breadcrumb`，breadcrumb 含序号/时间/线程ID，并强制 flush。
- `ThreadDO_150mm.py`：
    - 在 `Move/StepMove` 增加语句级 BEFORE/AFTER breadcrumb（覆盖 add_do_chan/cfg_samp_clk_timing/write/start/wait/stop）。
    - 增加 `DEBUG_DISABLE_DO` 调试开关（可快速隔离 DO 路径）。
    - 增加 DO 参数硬约束与 `DO_PARAM_INVALID` 保护。
    - `StepMove -> Move(target_pos=...)` 显式传目标，修复首次点击读旧值导致的“点两下才动一下”。
    - 移除 DO 工作线程内直接 `setValue`，统一改为 signal 回主线程设置 UI 数值。

## 下一步（待执行）
- 先跑 A 组：Camera OFF + DO ON，X/Y/Z 各连续点击 30 次。
- 如崩溃，立刻保存并对齐 `crash_dump.log` 与 `crash_breadcrumb.log` 的最后时间点。