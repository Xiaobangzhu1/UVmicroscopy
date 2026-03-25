# 排查与修复计划：进程意外退出问题

## 问题描述
程序在运行过程中会突然退出（Crash/Exit），且可能没有留下明显的报错信息。这通常由以下原因引起：
1. **底层崩溃 (Segmentation Fault/Access Violation)**：由 C/C++ 扩展库（如 `gxipy` 相机驱动, `artdaq` 板卡驱动, `PyQt5`, `opencv`, `numpy` 等）导致的内存错误。
2. **非正常退出调用**：代码中某处意外调用了 `sys.exit()`, `os._exit()`, 或 Qt 的 `CoreApplication.exit()`。
3. **未捕获的异常**：某些特殊线程或 Qt 事件循环中的异常导致程序终止。

## 修复步骤 (FIX Plan)

我准备按以下顺序修改代码，以捕捉“凶手”。

### 第零步：存档
- 操作：将代码上传到git

### 第一步：启用 Faulthandler (捕捉底层崩溃)
Python 的 `faulthandler` 模块可以在程序发生段错误（崩溃）时，强制将当前所有线程的 Python 调用栈打印到文件或控制台。
- **操作**：在 `SliceScanner.py` 最开头启用 `faulthandler`，并将崩溃日志重定向到 `crash_dump.log`。

### 第二步：增强生命周期日志 (排查正常退出)
排除程序是“以为自己该退出了”而退出的情况。
- **操作**：
    - 在 `MainWindow` 的 `closeEvent` 中增加日志，记录是谁触发了窗口关闭。
    - 在 `Stop_allThreads` 中增加日志，看是否是代码逻辑主动由于某些条件（如限位触发）调用了停止。

### 第三步：封装底层驱动调用 (隔离风险)
如果崩溃发生在特定硬件操作时（如相机采图、电机移动），需要“包裹”这些危险调用。
- **操作**：
    - 检查 `Camera.py` 中 `get_image` 等 C 库调用，确保没有非法指针访问。
    - 检查 `ThreadDO` 和 `ThreadDnS` 中的 numpy 数组操作，防止内存溢出导致的各种闪退。

### 第四步：Qt 异常捕获增强
Qt 的槽函数（Slot）中有时会吞掉异常或导致立即退出。
- **操作**：确保 `SliceScanner.py` 中的全局异常钩子 (`sys.excepthook`) 能正确拦截 Qt 事件循环抛出的错误。

## 验证方法
修改完成后，请运行程序复现“突然退出”的场景。
1. 如果生成了 `crash_dump.log` 或控制台打印了 `Fatal Python error`，说明是**底层驱动/库崩溃** --> 根据堆栈定位是哪个硬件驱动的问题。
2. 如果日志里最后一条是 `Weaver thread is doing: ...` 然后没了，说明是**硬崩溃且未被 faulthandler 捕获**（较少见，通常是电源或极端内存损坏）。
3. 如果日志里有 `MainWindow closing...`，说明是**程序逻辑**误判并主动关闭了。

请确认是否开始执行此计划？