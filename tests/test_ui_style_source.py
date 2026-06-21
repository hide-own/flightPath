from __future__ import annotations

from pathlib import Path


APP_SOURCE = Path(__file__).resolve().parents[1] / "flightpath_video" / "app.py"


def test_option_style_contract_is_encoded_in_main_window_source() -> None:
    source = APP_SOURCE.read_text(encoding="utf-8")

    assert 'setProperty("visualRole", "optionChip")' in source
    assert "setMinimumHeight(34)" in source
    assert "QRadioButton[visualRole=\"optionChip\"]:checked" in source
    assert "QCheckBox[visualRole=\"optionChip\"]:checked" in source
    assert "QSpinBox:disabled" in source
    assert "QSpinBox:disabled::up-button" in source


def test_radio_and_checkbox_checked_indicators_use_the_same_selected_fill() -> None:
    source = APP_SOURCE.read_text(encoding="utf-8")

    assert "QRadioButton[visualRole=\"optionChip\"]::indicator:checked" in source
    assert "QCheckBox[visualRole=\"optionChip\"]::indicator:checked" in source
    assert source.count("background: #65c7ff;") >= 2
    assert "border: 4px solid #65c7ff;" not in source
    assert "border-radius: 4px;" in source
