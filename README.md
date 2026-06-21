# 飞行日志轨迹视频生成工具

这是一个 Windows 桌面小工具，用来把 Mission Planner / ArduPilot 的 `.bin` 飞行日志生成带卫星地图背景的 `.mp4` 轨迹视频。

## 功能

- 选择 `.bin` 飞行日志文件。
- 自动解析 GPS 轨迹、任务航点、速度、高度。
- 默认按 `RelAlt > 2m` 自动截取真正飞行阶段，也可以使用全部日志。
- 真正飞行阶段默认带起飞前/降落后各 3 秒缓冲；未检测到真正飞行阶段时会提示并使用完整 GPS 轨迹作为明确 fallback。
- 使用 Esri World Imagery 卫星瓦片作为地图背景，并缓存到 `cache/tiles`。
- 红点按日志真实时间插值移动，不按点序号匀速播放。
- 可显示航点编号、轨迹、当前红点、高度、速度和进度条。
- 支持选择输出路径、分辨率、帧率和真实时间/压缩时长。
- 生成过程中可以取消；取消后不会把未完成的视频当作成功结果。
- 使用 `imageio-ffmpeg` 输出 `.mp4`，不要求系统 PATH 里已有 ffmpeg。

## 运行

如果已经创建 `.venv` 并安装依赖，双击：

```text
launch_flightpath_video.vbs
```

该入口使用 `.venv\Scripts\pythonw.exe` 启动，不会留下命令行窗口。若缺少虚拟环境或依赖，会显示中文启动错误，并把详细信息写入 `launch_error.log`。

开发调试也可以双击：

```bat
run_app.bat
```

或在 PowerShell 中运行：

```powershell
.\.venv\Scripts\python.exe -m flightpath_video
```

首次安装依赖：

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

## 离线地图说明

程序会把下载过的 Esri 卫星瓦片缓存到 `cache/tiles/esri_world_imagery`。没有网络时，如果当前飞行区域和缩放级别已有缓存，可以继续生成；如果缺少瓦片，会提示“地图下载失败，且本地没有缓存瓦片”。

清理缓存时可以关闭程序后删除 `cache/tiles/esri_world_imagery` 目录。下次生成同一区域视频时，程序会重新下载缺失瓦片。

## 验证

运行自动化测试：

```powershell
.\.venv\Scripts\python.exe -m pytest
```

OpenSpec 校验：

```powershell
openspec validate add-flight-log-trajectory-video-tool --strict
```
