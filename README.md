# 飞行日志轨迹视频生成工具

这是一个用于把 Mission Planner / ArduPilot `.bin` 飞行日志生成飞行轨迹视频的本地工具。

当前仓库保留了已验证的 Python/PySide6 MVP，同时正在迁移到新的本地 Web 架构：

```text
浏览器 Vue3 + Naive UI 界面
        ↓
localhost FastAPI 服务
        ↓
pymavlink 解析 / 地图瓦片缓存 / 视频导出
```

用户数据默认只在本机处理，不上传到云端。

## 当前能力

- 解析 Mission Planner / ArduPilot `.bin` 日志。
- 提取 GPS 轨迹、航点、相对高度、速度和日志时间。
- 默认按 `RelAlt > 2m` 识别真正飞行阶段。
- 使用 Esri World Imagery 卫星瓦片，并缓存到本地。
- 通过 FastAPI 提供本地解析任务、任务状态、进度事件、取消和瓦片接口。
- Vue3/Naive UI 本地 Web 界面已具备左侧操作栏、右侧地图工作区骨架、文件选择、时间模式、播放范围和日志摘要展示。
- 旧 PySide6 MVP 仍可作为临时 fallback 使用。

## 本地 Web 版运行

安装 Python 依赖：

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

安装前端依赖：

```powershell
cd web
npm install --no-audit --no-fund --ignore-scripts
```

构建浏览器界面：

```powershell
cd web
npm run build
```

双击启动：

```text
launch_flightpath_web.vbs
```

该入口会启动本机 FastAPI 服务，并自动打开浏览器访问本地页面。

开发调试也可以运行：

```powershell
.\.venv\Scripts\python.exe -m flightpath_video.web_launcher
```

## 旧 PySide6 版运行

如果需要使用旧 MVP：

```text
launch_flightpath_video.vbs
```

或：

```powershell
.\.venv\Scripts\python.exe -m flightpath_video
```

## 验证

Python 测试：

```powershell
.\.venv\Scripts\python.exe -m pytest
```

前端测试和构建：

```powershell
cd web
npm test
npm run build
```

OpenSpec 校验：

```powershell
openspec validate migrate-ui-to-local-web-fastapi-3d-preview --strict
```
