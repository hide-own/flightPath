from __future__ import annotations

from PySide6.QtWidgets import QGridLayout
from PySide6.QtWidgets import QApplication

from flightpath_video.app import MainWindow


def test_ui_defaults_and_cancel_visibility() -> None:
    app = QApplication.instance() or QApplication([])
    window = MainWindow()
    try:
        assert window.true_flight_radio.isChecked()
        assert window.real_time_radio.isChecked()
        assert window.resolution_combo.currentText() == "1280x720"
        assert window.fps_spin.value() == 24
        assert window.show_waypoints_check.isChecked()
        assert window.show_altitude_check.isChecked()
        assert window.show_speed_check.isChecked()
        assert window.show_progress_check.isChecked()
        assert not window.cancel_btn.isVisible()
        assert "飞行日志轨迹视频生成工具" in window.windowTitle()
    finally:
        window.close()
        app.processEvents()


def test_option_controls_have_clear_selected_and_disabled_states() -> None:
    app = QApplication.instance() or QApplication([])
    window = MainWindow()
    try:
        stylesheet = window.styleSheet()
        assert 'QRadioButton[visualRole="optionChip"]:checked' in stylesheet
        assert 'QCheckBox[visualRole="optionChip"]:checked' in stylesheet
        assert "QSpinBox:disabled" in stylesheet

        option_controls = (
            window.true_flight_radio,
            window.all_log_radio,
            window.real_time_radio,
            window.compress_time_radio,
            window.show_waypoints_check,
            window.show_altitude_check,
            window.show_speed_check,
            window.show_progress_check,
        )
        for control in option_controls:
            assert control.minimumHeight() >= 32
            assert control.property("visualRole") == "optionChip"

        assert not window.compress_spin.isEnabled()
        window.compress_time_radio.setChecked(True)
        assert window.compress_spin.isEnabled()
        window.real_time_radio.setChecked(True)
        assert not window.compress_spin.isEnabled()
    finally:
        window.close()
        app.processEvents()


def test_settings_rows_have_stable_layout_to_avoid_initial_squeezing() -> None:
    app = QApplication.instance() or QApplication([])
    window = MainWindow()
    try:
        assert isinstance(window.options_layout, QGridLayout)
        assert window.minimumHeight() >= 720
        assert window.options_group.minimumHeight() >= 330
        for row_widget in (
            window.range_row_widget,
            window.time_row_widget,
            window.compress_row_widget,
            window.display_row_widget,
        ):
            assert row_widget.minimumHeight() >= 40
    finally:
        window.close()
        app.processEvents()
