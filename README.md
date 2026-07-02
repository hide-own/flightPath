# 飞行日志轨迹视频生成工具

这是一个用于把 Mission Planner / ArduPilot `.bin` 飞行日志生成飞行轨迹视频的本地 Web 工具。

当前仓库只保留本地 Web 架构：

```text
浏览器 Vue3 + Naive UI 界面
        -> localhost FastAPI 服务
        -> pymavlink 解析 / 地图瓦片缓存 / 视频导出
```

用户数据默认只在本机处理，不上传到云端。

## 当前能力

- 解析 Mission Planner / ArduPilot `.bin` 日志。
- 提取 GPS 轨迹、航点、相对高度、速度和日志时间。
- 默认按 `RelAlt > 2m` 识别真正飞行阶段。
- 使用 Esri World Imagery 卫星瓦片，并缓存到本地。
- 通过 FastAPI 提供本地解析任务、任务状态、进度事件、取消、导出和瓦片接口。
- Vue3/Naive UI 本地 Web 界面提供左侧操作栏、右侧地图工作区、文件选择、时间模式、播放范围和日志摘要展示。

## 运行

安装 Python 依赖：

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

开发和测试环境还需要：

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
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
.\.venv\Scripts\python.exe -m flightpath_video
```

或：

```powershell
.\.venv\Scripts\python.exe -m flightpath_video.web_launcher
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
