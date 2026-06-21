from __future__ import annotations

import tempfile
import traceback
from pathlib import Path

from PIL import Image
from PIL.ImageQt import ImageQt
from PySide6.QtCore import QObject, Qt, QThread, Signal, Slot
from PySide6.QtGui import QFont, QFontDatabase, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QDialog,
    QFileDialog,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QProgressBar,
    QRadioButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from .models import FlightLogData
from .parser import LogParseError, parse_bin_log
from .renderer import CancellationToken, RenderCancelled, RenderOptions, format_seconds, render_preview_image, render_video


def configure_application_font(app: QApplication) -> None:
    font_paths = [
        "C:/Windows/Fonts/msyh.ttc",
        "C:/Windows/Fonts/simhei.ttf",
        "C:/Windows/Fonts/simsun.ttc",
    ]
    for font_path in font_paths:
        if Path(font_path).exists():
            QFontDatabase.addApplicationFont(font_path)
            break
    app.setFont(QFont("Microsoft YaHei", 10))


class GenerateWorker(QObject):
    progress = Signal(int, str)
    finished = Signal(str)
    cancelled = Signal(str)
    failed = Signal(str)

    def __init__(self, log_data: FlightLogData, options: RenderOptions) -> None:
        super().__init__()
        self.log_data = log_data
        self.options = options
        self.cancel_token = CancellationToken()

    @Slot()
    def cancel(self) -> None:
        self.cancel_token.cancel()

    @Slot()
    def run(self) -> None:
        try:
            render_video(self.log_data, self.options, self.progress.emit, cancel_check=self.cancel_token.is_cancelled)
        except RenderCancelled as exc:
            self.cancelled.emit(str(exc))
        except Exception as exc:
            self.failed.emit(f"{exc}\n\n{traceback.format_exc()}")
        else:
            self.finished.emit(str(self.options.output_path))


class PreviewWorker(QObject):
    finished = Signal(str)
    cancelled = Signal(str)
    failed = Signal(str)

    def __init__(self, log_data: FlightLogData, options: RenderOptions) -> None:
        super().__init__()
        self.log_data = log_data
        self.options = options
        self.cancel_token = CancellationToken()

    @Slot()
    def cancel(self) -> None:
        self.cancel_token.cancel()

    @Slot()
    def run(self) -> None:
        try:
            image = render_preview_image(self.log_data, self.options, cancel_check=self.cancel_token.is_cancelled)
            path = Path(tempfile.gettempdir()) / "flightpath_video_preview.png"
            image.save(path)
        except RenderCancelled as exc:
            self.cancelled.emit(str(exc))
        except Exception as exc:
            self.failed.emit(f"{exc}\n\n{traceback.format_exc()}")
        else:
            self.finished.emit(str(path))


class MainWindow(QWidget):
    def __init__(self) -> None:
        super().__init__()
        app = QApplication.instance()
        if app is not None:
            configure_application_font(app)
        self.setWindowTitle("飞行日志轨迹视频生成工具")
        self.resize(920, 760)
        self.setMinimumSize(760, 720)

        self.log_data: FlightLogData | None = None
        self.worker_thread: QThread | None = None
        self.worker: QObject | None = None

        self._build_ui()
        self._connect_signals()
        self._set_busy(False)

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(22, 20, 22, 20)
        root.setSpacing(14)
        title = QLabel("飞行日志轨迹视频生成工具")
        title.setObjectName("titleLabel")
        root.addWidget(title)

        file_group = QGroupBox("文件")
        file_layout = QGridLayout(file_group)
        file_layout.setHorizontalSpacing(12)
        file_layout.setVerticalSpacing(10)
        self.log_path_edit = QLineEdit()
        self.log_path_edit.setPlaceholderText("选择 Mission Planner / ArduPilot .bin 日志")
        self.choose_log_btn = QPushButton("选择 .bin")
        self.output_path_edit = QLineEdit()
        self.output_path_edit.setPlaceholderText("选择输出 .mp4 文件")
        self.choose_output_btn = QPushButton("选择保存位置")
        file_layout.addWidget(QLabel("日志文件："), 0, 0)
        file_layout.addWidget(self.log_path_edit, 0, 1)
        file_layout.addWidget(self.choose_log_btn, 0, 2)
        file_layout.addWidget(QLabel("输出文件："), 1, 0)
        file_layout.addWidget(self.output_path_edit, 1, 1)
        file_layout.addWidget(self.choose_output_btn, 1, 2)
        root.addWidget(file_group)

        self.options_group = QGroupBox("生成设置")
        self.options_group.setMinimumHeight(330)
        self.options_layout = QGridLayout(self.options_group)
        self.options_layout.setHorizontalSpacing(12)
        self.options_layout.setVerticalSpacing(12)
        self.options_layout.setColumnStretch(1, 1)
        self.map_combo = QComboBox()
        self.map_combo.addItem("卫星地图 - Esri World Imagery")
        self.map_combo.setEnabled(False)

        range_row = QHBoxLayout()
        range_row.setSpacing(8)
        self.true_flight_radio = QRadioButton("真正飞行阶段")
        self.all_log_radio = QRadioButton("全部日志")
        self.true_flight_radio.setChecked(True)
        self.range_group = QButtonGroup(self)
        self.range_group.addButton(self.true_flight_radio)
        self.range_group.addButton(self.all_log_radio)
        range_row.addWidget(self.true_flight_radio)
        range_row.addWidget(self.all_log_radio)
        range_row.addStretch()

        time_row = QHBoxLayout()
        time_row.setSpacing(8)
        self.real_time_radio = QRadioButton("真实时间")
        self.compress_time_radio = QRadioButton("压缩到指定时长")
        self.real_time_radio.setChecked(True)
        self.time_group = QButtonGroup(self)
        self.time_group.addButton(self.real_time_radio)
        self.time_group.addButton(self.compress_time_radio)
        time_row.addWidget(self.real_time_radio)
        time_row.addWidget(self.compress_time_radio)
        time_row.addStretch()

        self.compress_spin = QSpinBox()
        self.compress_spin.setRange(5, 36000)
        self.compress_spin.setValue(360)
        self.compress_spin.setSuffix(" 秒")
        self.compress_spin.setEnabled(False)
        self.compress_spin.setMinimumHeight(34)
        self.compress_spin.setToolTip("仅压缩到指定时长模式可用")

        display_row = QHBoxLayout()
        display_row.setSpacing(8)
        self.show_waypoints_check = QCheckBox("航点编号")
        self.show_altitude_check = QCheckBox("高度")
        self.show_speed_check = QCheckBox("速度")
        self.show_progress_check = QCheckBox("进度条")
        for checkbox in (
            self.show_waypoints_check,
            self.show_altitude_check,
            self.show_speed_check,
            self.show_progress_check,
        ):
            checkbox.setChecked(True)
            display_row.addWidget(checkbox)
        display_row.addStretch()

        for option_control in (
            self.true_flight_radio,
            self.all_log_radio,
            self.real_time_radio,
            self.compress_time_radio,
            self.show_waypoints_check,
            self.show_altitude_check,
            self.show_speed_check,
            self.show_progress_check,
        ):
            option_control.setProperty("visualRole", "optionChip")
            option_control.setMinimumHeight(34)
            option_control.setCursor(Qt.CursorShape.PointingHandCursor)

        self.resolution_combo = QComboBox()
        for label, size in (("1280x720", (1280, 720)), ("1920x1080", (1920, 1080)), ("854x480", (854, 480))):
            self.resolution_combo.addItem(label, size)
        self.fps_spin = QSpinBox()
        self.fps_spin.setRange(1, 60)
        self.fps_spin.setValue(24)
        self.fps_spin.setSuffix(" fps")

        def setting_label(text: str) -> QLabel:
            label = QLabel(text)
            label.setObjectName("settingLabel")
            label.setMinimumWidth(72)
            return label

        def row_container(layout: QHBoxLayout) -> QWidget:
            widget = QWidget()
            widget.setObjectName("settingRow")
            widget.setMinimumHeight(42)
            layout.setContentsMargins(0, 0, 0, 0)
            widget.setLayout(layout)
            return widget

        def single_control_row(control: QWidget) -> QWidget:
            layout = QHBoxLayout()
            layout.setContentsMargins(0, 0, 0, 0)
            layout.addWidget(control)
            return row_container(layout)

        self.map_row_widget = single_control_row(self.map_combo)
        self.range_row_widget = row_container(range_row)
        self.time_row_widget = row_container(time_row)
        self.compress_row_widget = single_control_row(self.compress_spin)
        self.display_row_widget = row_container(display_row)
        self.resolution_row_widget = single_control_row(self.resolution_combo)
        self.fps_row_widget = single_control_row(self.fps_spin)

        option_rows = (
            ("地图背景：", self.map_row_widget),
            ("播放范围：", self.range_row_widget),
            ("时间模式：", self.time_row_widget),
            ("压缩时长：", self.compress_row_widget),
            ("显示：", self.display_row_widget),
            ("分辨率：", self.resolution_row_widget),
            ("帧率：", self.fps_row_widget),
        )
        for row, (label_text, row_widget) in enumerate(option_rows):
            self.options_layout.addWidget(setting_label(label_text), row, 0, Qt.AlignmentFlag.AlignVCenter)
            self.options_layout.addWidget(row_widget, row, 1)
            self.options_layout.setRowMinimumHeight(row, 42)
        root.addWidget(self.options_group)

        self.info_label = QLabel("日志信息：尚未选择日志")
        self.info_label.setObjectName("infoPanel")
        self.info_label.setWordWrap(True)
        self.info_label.setFrameShape(QFrame.Shape.StyledPanel)
        root.addWidget(self.info_label)

        button_row = QHBoxLayout()
        self.preview_btn = QPushButton("预览轨迹")
        self.generate_btn = QPushButton("生成视频")
        self.generate_btn.setObjectName("primaryButton")
        self.cancel_btn = QPushButton("取消")
        self.cancel_btn.setObjectName("dangerButton")
        self.cancel_btn.setVisible(False)
        self.cancel_btn.setEnabled(False)
        button_row.addStretch()
        button_row.addWidget(self.preview_btn)
        button_row.addWidget(self.generate_btn)
        button_row.addWidget(self.cancel_btn)
        root.addLayout(button_row)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.status_label = QLabel("状态：等待选择日志")
        self.status_label.setObjectName("idleStatus")
        root.addWidget(QLabel("进度："))
        root.addWidget(self.progress_bar)
        root.addWidget(self.status_label)

        self.setStyleSheet(
            """
            QWidget {
                background: #101820;
                color: #e8f0f7;
                font-family: "Microsoft YaHei", "Segoe UI";
                font-size: 14px;
            }
            #titleLabel {
                color: #f6fbff;
                font-size: 24px;
                font-weight: 700;
                padding: 4px 0 2px 0;
            }
            QGroupBox {
                background: #172331;
                border: 1px solid #2c4256;
                border-radius: 8px;
                font-weight: 700;
                margin-top: 12px;
                padding: 14px 12px 12px 12px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 12px;
                padding: 0 6px;
                color: #8ed6ff;
            }
            QLabel { color: #e8f0f7; }
            #settingLabel {
                background: transparent;
                color: #e8f0f7;
                font-weight: 700;
            }
            #settingRow {
                background: transparent;
            }
            QLineEdit, QComboBox, QSpinBox {
                background: #0f1720;
                border: 1px solid #395369;
                border-radius: 6px;
                color: #f6fbff;
                min-height: 20px;
                padding: 4px 8px;
                selection-background-color: #238bd6;
            }
            QLineEdit:focus, QComboBox:focus, QSpinBox:focus { border-color: #65c7ff; }
            QSpinBox:disabled {
                background: #0b1118;
                border: 1px dashed #2a3a48;
                color: #536575;
            }
            QSpinBox:disabled::up-button, QSpinBox:disabled::down-button {
                background: #0b1118;
                border-left: 1px solid #253442;
            }
            QRadioButton, QCheckBox {
                spacing: 8px;
                color: #e8f0f7;
            }
            QRadioButton[visualRole="optionChip"], QCheckBox[visualRole="optionChip"] {
                background: #132230;
                border: 1px solid #33495d;
                border-radius: 7px;
                color: #cfe1ef;
                font-weight: 600;
                padding: 6px 12px;
                min-height: 20px;
            }
            QRadioButton[visualRole="optionChip"]:hover, QCheckBox[visualRole="optionChip"]:hover {
                background: #1a2d3d;
                border-color: #4a6a83;
                color: #f6fbff;
            }
            QRadioButton[visualRole="optionChip"]:checked, QCheckBox[visualRole="optionChip"]:checked {
                background: #1f4f68;
                border: 1px solid #65c7ff;
                color: #ffffff;
                font-weight: 700;
            }
            QRadioButton[visualRole="optionChip"]:disabled, QCheckBox[visualRole="optionChip"]:disabled {
                background: #141d27;
                border-color: #263544;
                color: #6f8192;
            }
            QRadioButton[visualRole="optionChip"]::indicator {
                width: 14px;
                height: 14px;
                border-radius: 7px;
                border: 1px solid #57748c;
                background: #0d1620;
            }
            QRadioButton[visualRole="optionChip"]::indicator:checked {
                border: 1px solid #8ed6ff;
                background: #65c7ff;
            }
            QRadioButton[visualRole="optionChip"]::indicator:unchecked:hover {
                border-color: #8ed6ff;
            }
            QCheckBox[visualRole="optionChip"]::indicator {
                width: 15px;
                height: 15px;
                border-radius: 4px;
                border: 1px solid #57748c;
                background: #0d1620;
            }
            QCheckBox[visualRole="optionChip"]::indicator:checked {
                background: #65c7ff;
                border-color: #8ed6ff;
            }
            QCheckBox[visualRole="optionChip"]::indicator:unchecked:hover {
                border-color: #8ed6ff;
            }
            QPushButton {
                background: #24384a;
                border: 1px solid #3a5368;
                border-radius: 7px;
                color: #f6fbff;
                padding: 8px 16px;
                font-weight: 600;
            }
            QPushButton:hover { background: #2d485d; }
            QPushButton:disabled {
                color: #748595;
                background: #182330;
                border-color: #223241;
            }
            #primaryButton {
                background: #1f9d72;
                border-color: #2fcf99;
                color: #ffffff;
            }
            #primaryButton:hover { background: #25b886; }
            #primaryButton:disabled {
                color: #7f958d;
                background: #1a332b;
                border-color: #25483c;
            }
            #dangerButton {
                background: #6e2c34;
                border-color: #b94a57;
                color: #ffffff;
            }
            #dangerButton:hover { background: #8a3540; }
            QProgressBar {
                background: #0f1720;
                border: 1px solid #395369;
                border-radius: 8px;
                color: #ffffff;
                height: 20px;
                text-align: center;
            }
            QProgressBar::chunk {
                background: #2fcf99;
                border-radius: 7px;
            }
            #infoPanel {
                background: #0f1720;
                border: 1px solid #31495e;
                border-radius: 8px;
                padding: 10px;
            }
            #idleStatus { color: #a9bfd2; }
            #workingStatus { color: #8ed6ff; }
            #successStatus { color: #7ee1ad; }
            #warningStatus { color: #ffd166; }
            #errorStatus { color: #ff8b94; }
            """
        )

    def _connect_signals(self) -> None:
        self.choose_log_btn.clicked.connect(self.choose_log_file)
        self.choose_output_btn.clicked.connect(self.choose_output_file)
        self.preview_btn.clicked.connect(self.preview_track)
        self.generate_btn.clicked.connect(self.generate_video)
        self.cancel_btn.clicked.connect(self.cancel_active_work)
        self.compress_time_radio.toggled.connect(self.compress_spin.setEnabled)
        self.log_path_edit.editingFinished.connect(self.parse_current_log)

    @Slot()
    def choose_log_file(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "选择 .bin 飞行日志", "", "ArduPilot Bin Log (*.bin);;All Files (*)")
        if not path:
            return
        self.log_path_edit.setText(path)
        output_path = str(Path(path).with_name(f"{Path(path).stem}_track.mp4"))
        self.output_path_edit.setText(output_path)
        self.parse_current_log()

    @Slot()
    def choose_output_file(self) -> None:
        start = self.output_path_edit.text().strip() or "flight_track.mp4"
        path, _ = QFileDialog.getSaveFileName(self, "选择输出视频", start, "MP4 Video (*.mp4)")
        if not path:
            return
        if not path.lower().endswith(".mp4"):
            path += ".mp4"
        self.output_path_edit.setText(path)

    @Slot()
    def parse_current_log(self) -> None:
        path = self.log_path_edit.text().strip()
        if not path:
            return
        self._set_status("状态：正在解析日志...", "working")
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            self.log_data = parse_bin_log(path)
        except LogParseError as exc:
            self.log_data = None
            QMessageBox.critical(self, "解析失败", str(exc))
            self.info_label.setText("日志信息：解析失败")
            self._set_status("状态：解析失败", "error")
        except Exception as exc:
            self.log_data = None
            QMessageBox.critical(self, "解析失败", f"{exc}\n\n{traceback.format_exc()}")
            self.info_label.setText("日志信息：解析失败")
            self._set_status("状态：解析失败", "error")
        else:
            self._update_log_info()
            self._set_status("状态：日志解析完成", "success")
        finally:
            QApplication.restoreOverrideCursor()

    @Slot()
    def preview_track(self) -> None:
        if not self._ensure_ready(require_output=False):
            return
        options = self._make_options(output_path=Path(tempfile.gettempdir()) / "flightpath_preview.mp4")
        self._set_busy(True)
        self._set_status("状态：正在生成预览...", "working")
        self.progress_bar.setValue(0)

        thread = QThread(self)
        worker = PreviewWorker(self.log_data, options)  # type: ignore[arg-type]
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.finished.connect(self._show_preview)
        worker.cancelled.connect(self._worker_cancelled)
        worker.failed.connect(self._worker_failed)
        worker.finished.connect(thread.quit)
        worker.cancelled.connect(thread.quit)
        worker.failed.connect(thread.quit)
        thread.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        thread.finished.connect(lambda: self._set_busy(False))
        self.worker_thread = thread
        self.worker = worker
        thread.start()

    @Slot()
    def generate_video(self) -> None:
        if not self._ensure_ready(require_output=True):
            return
        output_path = Path(self.output_path_edit.text().strip())
        if output_path.exists():
            result = QMessageBox.question(self, "覆盖确认", f"输出文件已存在，是否覆盖？\n{output_path}")
            if result != QMessageBox.StandardButton.Yes:
                return

        options = self._make_options(output_path=output_path)
        self._set_busy(True)
        self.progress_bar.setValue(0)
        self._set_status("状态：准备生成视频...", "working")

        thread = QThread(self)
        worker = GenerateWorker(self.log_data, options)  # type: ignore[arg-type]
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.progress.connect(self._worker_progress)
        worker.finished.connect(self._generation_finished)
        worker.cancelled.connect(self._worker_cancelled)
        worker.failed.connect(self._worker_failed)
        worker.finished.connect(thread.quit)
        worker.cancelled.connect(thread.quit)
        worker.failed.connect(thread.quit)
        thread.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        thread.finished.connect(lambda: self._set_busy(False))
        self.worker_thread = thread
        self.worker = worker
        thread.start()

    def _make_options(self, output_path: Path) -> RenderOptions:
        width, height = self.resolution_combo.currentData()
        compressed = self.compress_spin.value() if self.compress_time_radio.isChecked() else None
        return RenderOptions(
            output_path=output_path,
            width=int(width),
            height=int(height),
            fps=self.fps_spin.value(),
            true_flight_only=self.true_flight_radio.isChecked(),
            compressed_duration_s=compressed,
            show_waypoints=self.show_waypoints_check.isChecked(),
            show_altitude=self.show_altitude_check.isChecked(),
            show_speed=self.show_speed_check.isChecked(),
            show_progress=self.show_progress_check.isChecked(),
        )

    def _ensure_ready(self, require_output: bool) -> bool:
        if self.log_data is None:
            self.parse_current_log()
        if self.log_data is None:
            return False
        if require_output and not self.output_path_edit.text().strip():
            QMessageBox.warning(self, "缺少输出路径", "请先选择输出 .mp4 文件。")
            return False
        return True

    def _update_log_info(self) -> None:
        if self.log_data is None:
            return
        full_duration = format_seconds(self.log_data.total_duration_s)
        flight_duration = format_seconds(self.log_data.selected_duration_s(True))
        fallback_note = ""
        if not self.log_data.true_flight_detected():
            fallback_note = "，未检测到真正飞行阶段，默认使用完整 GPS 轨迹"
        text = (
            "日志信息："
            f"GPS 点 {self.log_data.gps_count} 个，"
            f"日志时长 {full_duration}，"
            f"真正飞行阶段 {flight_duration}，"
            f"最高高度 {self.log_data.max_altitude_m:.1f} m，"
            f"最大速度 {self.log_data.max_speed_m_s:.1f} m/s，"
            f"航点 {len(self.log_data.waypoints)} 个"
            f"{fallback_note}"
        )
        self.info_label.setText(text)

    @Slot(int, str)
    def _worker_progress(self, percent: int, status: str) -> None:
        self.progress_bar.setValue(percent)
        self._set_status(f"状态：{status}", "working")

    @Slot(str)
    def _generation_finished(self, path: str) -> None:
        self.progress_bar.setValue(100)
        self._set_status(f"状态：生成完成 {path}", "success")
        QMessageBox.information(self, "生成完成", f"视频已生成：\n{path}")

    @Slot(str)
    def _show_preview(self, image_path: str) -> None:
        self.progress_bar.setValue(100)
        self._set_status("状态：预览完成", "success")
        dialog = QDialog(self)
        dialog.setWindowTitle("轨迹预览")
        layout = QVBoxLayout(dialog)
        label = QLabel()
        with Image.open(image_path) as image:
            pixmap = QPixmap.fromImage(ImageQt(image.copy()))
        label.setPixmap(pixmap.scaled(960, 540, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(label)
        dialog.resize(1000, 600)
        dialog.exec()

    @Slot(str)
    def _worker_failed(self, message: str) -> None:
        self._set_status("状态：失败", "error")
        QMessageBox.critical(self, "操作失败", message)

    @Slot(str)
    def _worker_cancelled(self, message: str) -> None:
        self.progress_bar.setValue(0)
        self._set_status(f"状态：已取消 {message}", "warning")

    @Slot()
    def cancel_active_work(self) -> None:
        if self.worker is not None and hasattr(self.worker, "cancel"):
            self.cancel_btn.setEnabled(False)
            self._set_status("状态：正在取消...", "warning")
            self.worker.cancel()  # type: ignore[attr-defined]

    def _set_busy(self, busy: bool) -> None:
        for widget in (
            self.choose_log_btn,
            self.choose_output_btn,
            self.preview_btn,
            self.generate_btn,
            self.log_path_edit,
            self.output_path_edit,
            self.true_flight_radio,
            self.all_log_radio,
            self.real_time_radio,
            self.compress_time_radio,
            self.compress_spin,
            self.show_waypoints_check,
            self.show_altitude_check,
            self.show_speed_check,
            self.show_progress_check,
            self.resolution_combo,
            self.fps_spin,
        ):
            widget.setEnabled(not busy)
        self.compress_spin.setEnabled(not busy and self.compress_time_radio.isChecked())
        self.cancel_btn.setVisible(busy)
        self.cancel_btn.setEnabled(busy)
        if not busy:
            self.worker = None
            self.worker_thread = None

    def _set_status(self, text: str, state: str = "idle") -> None:
        names = {
            "idle": "idleStatus",
            "working": "workingStatus",
            "success": "successStatus",
            "warning": "warningStatus",
            "error": "errorStatus",
        }
        self.status_label.setObjectName(names.get(state, "idleStatus"))
        self.status_label.style().unpolish(self.status_label)
        self.status_label.style().polish(self.status_label)
        self.status_label.setText(text)


def main() -> int:
    app = QApplication([])
    configure_application_font(app)
    window = MainWindow()
    window.show()
    return app.exec()
