import os
import sys

import tempfile
import shutil
import subprocess
import tomllib

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QScrollArea, QGridLayout,
    QMessageBox, QFrame, QSizePolicy
)
from PyQt6.QtGui import QIcon, QPixmap, QFont, QColor,  QFontDatabase, QPainter, QAction
from PyQt6.QtCore import Qt, QSize, pyqtSignal, QRect, QPropertyAnimation, pyqtProperty

try:
    from PyQt6.QtSvg import QSvgRenderer
except ImportError:
    QSvgRenderer = None

from touchbar_enhancer.helpers import build_config_toml, CUPERTINO_ICONS_MAP, TINY_DFR_BUILTIN_ICONS, standard_media_layout

class ToggleSwitch(QWidget):
    toggled = pyqtSignal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(50, 26)
        self._checked = False
        self._position = 0.0

        self.animation = QPropertyAnimation(self, b"position")
        self.animation.setDuration(150)

    @pyqtProperty(float)
    def position(self):
        return self._position

    @position.setter
    def position(self, pos):
        self._position = pos
        self.update()

    def isChecked(self):
        return self._checked

    def setChecked(self, checked):
        self._checked = checked
        self.animation.setStartValue(self._position)
        self.animation.setEndValue(1.0 if checked else 0.0)
        self.animation.start()
        self.toggled.emit(checked)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.setChecked(not self._checked)
            super().mouseReleaseEvent(event)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        bg_color = QColor("#0A84FF") if self._checked else QColor("#444444")
        painter.setBrush(bg_color)
        painter.setPen(Qt.PenStyle.NoPen)
        rect = QRect(0, 0, self.width(), self.height())
        painter.drawRoundedRect(rect, self.height() // 2, self.height() // 2)

        knob_color = QColor("#FFFFFF")
        painter.setBrush(knob_color)
        knob_radius = self.height() - 6
        knob_x = int(3 + self._position * (self.width() - knob_radius - 6))

        knob_rect = QRect(knob_x, 3, knob_radius, knob_radius)
        painter.drawEllipse(knob_rect)
        painter.end()

PRESETS = [
    {"name": "Delete", "icon": "delete_solid", "action": "Delete", "label": "Delete (Trash)"},
    {"name": "Screenshot", "icon": "camera_fill", "action": "Print", "label": "Screenshot (Camera)"},
    {"name": "Mute", "icon": "volume_off", "action": "Mute", "label": "Mute (Speaker Off)"},
    {"name": "Volume Down", "icon": "volume_down", "action": "VolumeDown", "label": "Volume Down"},
    {"name": "Volume Up", "icon": "volume_up", "action": "VolumeUp", "label": "Volume Up"},
    {"name": "Play / Pause", "icon": "play_pause", "action": "PlayPause", "label": "Play / Pause"},
    {"name": "Next Track", "icon": "fast_forward", "action": "NextSong", "label": "Next Track"},
    {"name": "Previous Track", "icon": "fast_rewind", "action": "PreviousSong", "label": "Previous Track"},
    {"name": "Brightness Down", "icon": "brightness_low", "action": "BrightnessDown", "label": "Brightness Down"},
    {"name": "Brightness Up", "icon": "brightness_high", "action": "BrightnessUp", "label": "Brightness Up"},
    {"name": "Kbd Light Down", "icon": "backlight_low", "action": "IllumDown", "label": "Kbd Light Down"},
    {"name": "Kbd Light Up", "icon": "backlight_high", "action": "IllumUp", "label": "Kbd Light Up"},
    {"name": "Search", "icon": "search", "action": "Search", "label": "Search (Magnifier)"},
    {"name": "Mic Mute", "icon": "mic_off", "action": "MicMute", "label": "Mic Mute"},
    {"name": "Lock Screen", "icon": "lock_fill", "action": "Sleep", "label": "Lock Screen"},
    {"name": "Show Desktop", "icon": "desktopcomputer", "action": "LeftMeta, D", "label": "Show Desktop (Super+D)"},
    {"name": "Terminal", "icon": "chevron_left_slash_chevron_right", "action": "LeftCtrl, LeftAlt, T", "label": "Terminal (Ctrl+Alt+T)"},
    {"name": "Sleep", "icon": "moon_zzz_fill", "action": "Sleep", "label": "Sleep (Suspend)"},
    {"name": "Files", "icon": "folder_fill", "action": "LeftMeta, E", "label": "Files (Super+E)"},
    {"name": "Calculator", "icon": "percent", "action": "Calc", "label": "Calculator"},
    {"name": "Spacer", "icon": "", "action": "", "label": "Flexible Spacer", "type": "Spacer", "stretch": 5},
]

class ToolboxButton(QPushButton):
    def __init__(self, preset, parent=None):
        super().__init__(parent)
        self.preset = preset
        self.setObjectName("presetBtn")
        self.setFixedHeight(38)

        # Create a small + badge in the top-right corner
        self.badge = QLabel("+", self)
        self.badge.setObjectName("badge")
        self.badge.setStyleSheet("""
            QLabel#badge {
                background-color: #0A84FF;
                color: white;
                font-size: 10px;
                font-weight: 800;
                border-radius: 7px;
                border: none;
            }
        """)
        self.badge.setFixedSize(14, 14)
        self.badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.badge.hide()

        # Set ToolTip (has native delay, satisfying the slower popup requirement)
        self.setToolTip(f"Add {preset.get('label', preset['name'])}")

    def enterEvent(self, event):
        super().enterEvent(event)
        self.badge.move(self.width() - 17, 3)
        self.badge.show()

    def leaveEvent(self, event):
        super().leaveEvent(event)
        self.badge.hide()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self.badge.isVisible():
            self.badge.move(self.width() - 17, 3)

class TouchbarEnhancer(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Touch Bar Enhancer")
        self.resize(1100, 750)
        self.setMinimumSize(800, 600)
        self.setStyleSheet(self.get_stylesheet())

        self.settings = {
            "media_default": True,
            "show_outlines": True,
            "enable_pixel_shift": False,
            "adaptive_brightness": True,
            "font_template": ":bold"
        }
        self.media_specs = standard_media_layout()
        self.primary_specs = [
            {"type": "Text", "val": f"F{i}", "action": f"F{i}", "stretch": 1} for i in range(1, 13)
        ]
        self.layout_specs = self.media_specs

        self.init_ui()
        self.load_active_config()

    def reset_to_defaults(self):
        self.media_specs = standard_media_layout()
        self.primary_specs = [
            {"type": "Text", "val": f"F{i}", "action": f"F{i}", "stretch": 1} for i in range(1, 13)
        ]
        if hasattr(self, 'layer_toggle') and self.layer_toggle.isChecked():
            self.layout_specs = self.media_specs
        else:
            self.layout_specs = self.primary_specs
        self.render_preview()

    def get_stylesheet(self):
        return """
        QMainWindow {
            background-color: #0f0f11;
            color: #ffffff;
        }
        QWidget {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            color: #ffffff;
        }
        QLabel {
            font-size: 14px;
        }
        QScrollArea {
            border: none;
            background-color: transparent;
        }
        QScrollBar:vertical {
            border: none;
            background: #2a2a2a;
            width: 8px;
            margin: 0px;
            border-radius: 4px;
        }
        QScrollBar::handle:vertical {
            background: #555555;
            min-height: 20px;
            border-radius: 4px;
        }
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
            height: 0px;
        }
        QPushButton {
            background-color: #2c2c2e;
            border: 1px solid #3a3a3c;
            border-radius: 8px;
            padding: 10px;
            font-weight: 600;
        }
        QPushButton:hover {
            background-color: #3a3a3c;
            border: 1px solid #48484a;
        }
        QPushButton:pressed {
            background-color: #48484a;
        }
        #deployBtn {
            background-color: #0A84FF;
            color: white;
            border: none;
            font-size: 15px;
            font-weight: bold;
            padding: 14px;
            border-radius: 10px;
        }
        #deployBtn:hover {
            background-color: #0070E0;
        }
        #resetBtn {
            background-color: transparent;
            border: 1px solid #ff453a;
            color: #ff453a;
            font-size: 14px;
            font-weight: 600;
            padding: 10px;
            border-radius: 8px;
        }
        #resetBtn:hover {
            background-color: rgba(255, 69, 58, 0.1);
        }
        #previewContainer {
            background-color: #000000;
            border-radius: 14px;
            border: 2px solid #2c2c2e;
        }
        #presetBtn {
            background-color: #1c1c1e;
            border: 1px solid #2c2c2e;
            border-radius: 8px;
            padding: 8px;
            font-size: 13px;
            font-weight: 500;
        }
        #presetBtn:hover {
            background-color: #2c2c2e;
            border-color: #3a3a3c;
        }
        .Card {
            background-color: #1c1c1e;
            border-radius: 12px;
            border: 1px solid #2c2c2e;
        }
        .CardHeader {
            font-size: 18px;
            font-weight: bold;
            color: #ffffff;
        }
        .SettingLabel {
            font-size: 14px;
            color: #d1d1d6;
        }
        """

    def create_setting_row(self, label_text, toggle_switch):
        row = QHBoxLayout()
        lbl = QLabel(label_text)
        lbl.setProperty("class", "SettingLabel")
        row.addWidget(lbl)
        row.addStretch()
        row.addWidget(toggle_switch)
        return row

    def init_ui(self):
        menubar = self.menuBar()
        help_menu = menubar.addMenu("Help")

        about_action = QAction("About Touch Bar Enhancer", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(40, 40, 40, 40)
        main_layout.setSpacing(30)

        # Header Area
        header_layout = QHBoxLayout()
        title_layout = QVBoxLayout()
        header = QLabel("Touch Bar Enhancer")
        header.setStyleSheet("font-size: 28px; font-weight: 800; letter-spacing: 0.5px; color: #ffffff;")
        subtitle = QLabel("Design your ideal Touch Bar layout")
        subtitle.setStyleSheet("font-size: 14px; color: #8e8e93;")
        title_layout.addWidget(header)
        title_layout.addWidget(subtitle)
        header_layout.addLayout(title_layout)

        header_layout.addStretch()

        # Layer Toggle in Header
        toggle_container = QFrame()
        toggle_container.setProperty("class", "Card")
        toggle_container_layout = QHBoxLayout(toggle_container)
        toggle_container_layout.setContentsMargins(15, 10, 15, 10)
        toggle_container_layout.setSpacing(12)

        self.lbl_f1 = QLabel("F1-F12")
        self.lbl_media = QLabel("Media Keys")
        self.layer_toggle = ToggleSwitch()
        self.layer_toggle.toggled.connect(self.on_layer_toggle)

        toggle_container_layout.addWidget(self.lbl_f1)
        toggle_container_layout.addWidget(self.layer_toggle)
        toggle_container_layout.addWidget(self.lbl_media)

        header_layout.addWidget(toggle_container)
        main_layout.addLayout(header_layout)

        # Preview Section
        preview_label = QLabel("Active Layout (Click to remove)")
        preview_label.setStyleSheet("font-size: 15px; font-weight: 600; color: #aeaeb2;")
        main_layout.addWidget(preview_label)

        self.preview_container = QFrame()
        self.preview_container.setObjectName("previewContainer")
        self.preview_container.setFixedHeight(60)

        self.preview_layout = QHBoxLayout(self.preview_container)
        self.preview_layout.setContentsMargins(8, 8, 8, 8)
        self.preview_layout.setSpacing(6)
        main_layout.addWidget(self.preview_container)

        self.on_layer_toggle(self.settings["media_default"])
        self.layer_toggle._checked = self.settings["media_default"]
        self.layer_toggle.position = 1.0 if self.settings["media_default"] else 0.0

        # Main Content Area (Settings + Toolbox)
        content_layout = QHBoxLayout()
        content_layout.setSpacing(30)
        main_layout.addLayout(content_layout)

        # Settings Card (Left Column)
        settings_card = QFrame()
        settings_card.setProperty("class", "Card")
        settings_layout = QVBoxLayout(settings_card)
        settings_layout.setContentsMargins(25, 25, 25, 25)
        settings_layout.setSpacing(20)

        settings_header = QLabel("Settings")
        settings_header.setProperty("class", "CardHeader")
        settings_layout.addWidget(settings_header)

        # Settings Toggles
        self.chk_show_outlines = ToggleSwitch()
        self.chk_pixel_shift = ToggleSwitch()
        self.chk_adaptive_brightness = ToggleSwitch()

        self.chk_show_outlines.setChecked(self.settings["show_outlines"])
        self.chk_pixel_shift.setChecked(self.settings["enable_pixel_shift"])
        self.chk_adaptive_brightness.setChecked(self.settings["adaptive_brightness"])

        settings_layout.addLayout(self.create_setting_row("Show Button Outlines", self.chk_show_outlines))
        settings_layout.addLayout(self.create_setting_row("Enable Pixel Shift", self.chk_pixel_shift))
        settings_layout.addLayout(self.create_setting_row("Adaptive Brightness", self.chk_adaptive_brightness))

        settings_layout.addStretch()

        reset_btn = QPushButton("Reset to Defaults")
        reset_btn.setObjectName("resetBtn")
        reset_btn.clicked.connect(self.reset_to_defaults)
        settings_layout.addWidget(reset_btn)

        deploy_btn = QPushButton("Deploy to Touchbar")
        deploy_btn.setObjectName("deployBtn")
        deploy_btn.clicked.connect(self.deploy_config)
        settings_layout.addWidget(deploy_btn)

        content_layout.addWidget(settings_card, 1)

        # Toolbox Card (Right Column)
        toolbox_card = QFrame()
        toolbox_card.setProperty("class", "Card")
        toolbox_layout = QVBoxLayout(toolbox_card)
        toolbox_layout.setContentsMargins(25, 25, 25, 25)
        toolbox_layout.setSpacing(15)

        toolbox_header = QLabel("Toolbox (Click to add)")
        toolbox_header.setProperty("class", "CardHeader")
        toolbox_layout.addWidget(toolbox_header)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_content = QWidget()
        scroll_content.setStyleSheet("background: transparent;")
        self.grid_layout = QGridLayout(scroll_content)
        self.grid_layout.setSpacing(10)
        self.grid_layout.setContentsMargins(0, 0, 10, 0) # margin for scrollbar

        row = 0
        col = 0
        for preset in PRESETS:
            btn = ToolboxButton(preset)

            icon_name = preset.get("icon", "")
            pixmap = self.get_icon_pixmap(icon_name)
            if pixmap:
                btn.setIcon(QIcon(pixmap))
                btn.setIconSize(QSize(20, 20))

            if preset.get("type") == "Spacer":
                btn.setText("Spacer")

            btn.clicked.connect(lambda checked, p=preset: self.add_to_layout(p))

            self.grid_layout.addWidget(btn, row, col)
            col += 1
            if col > 2: # 3 columns to fit nicely in the right pane
                col = 0
                row += 1

        scroll.setWidget(scroll_content)
        toolbox_layout.addWidget(scroll)

        content_layout.addWidget(toolbox_card, 2)

    def on_layer_toggle(self, checked):
        if checked:
            self.lbl_media.setStyleSheet("font-size: 14px; font-weight: bold; color: #ffffff;")
            self.lbl_f1.setStyleSheet("font-size: 14px; font-weight: bold; color: #888888;")
            self.layout_specs = self.media_specs
        else:
            self.lbl_media.setStyleSheet("font-size: 14px; font-weight: bold; color: #888888;")
            self.lbl_f1.setStyleSheet("font-size: 14px; font-weight: bold; color: #ffffff;")
            self.layout_specs = self.primary_specs
        self.settings["media_default"] = checked
        self.render_preview()

    def get_icon_pixmap(self, icon_name, size=64):
        if not icon_name:
            return None

        if icon_name in TINY_DFR_BUILTIN_ICONS:
            svg_path = f"/usr/share/tiny-dfr/{icon_name}.svg"
            if os.path.exists(svg_path):
                if QSvgRenderer is not None:
                    renderer = QSvgRenderer(svg_path)
                    if renderer.isValid():
                        pixmap = QPixmap(size, size)
                        pixmap.fill(Qt.GlobalColor.transparent)
                        painter = QPainter(pixmap)
                        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
                        renderer.render(painter)
                        painter.end()
                        return pixmap

        codepoint = CUPERTINO_ICONS_MAP.get(icon_name)
        if codepoint is not None:
            pixmap = QPixmap(size, size)
            pixmap.fill(Qt.GlobalColor.transparent)

            painter = QPainter(pixmap)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)

            font = QFont("CupertinoIcons")
            font.setPixelSize(int(size * 0.8)) # slightly smaller to fit
            painter.setFont(font)
            painter.setPen(QColor(255, 255, 255))

            char = chr(codepoint)
            painter.drawText(QRect(0, 0, size, size), Qt.AlignmentFlag.AlignCenter, char)
            painter.end()
            return pixmap
        return None

    def add_to_layout(self, preset):
        item = {
            "type": preset.get("type", "Icon"),
            "val": preset.get("icon", preset.get("name", "")),
            "action": preset.get("action", ""),
            "stretch": preset.get("stretch", 1),
            "spacer_type": "flexible" if preset.get("stretch", 1) > 2 else ("small" if preset.get("stretch", 1) == 1 else "large")
        }
        self.layout_specs.append(item)
        self.render_preview()

    def remove_from_layout(self, index):
        if 0 <= index < len(self.layout_specs):
            self.layout_specs.pop(index)
            self.render_preview()

    def render_preview(self):
        # Clear current preview
        while self.preview_layout.count():
            child = self.preview_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        for i, item in enumerate(self.layout_specs):
            btn = QPushButton()
            btn.setToolTip(f"{item.get('action', '')} (Click to remove)")
            btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
            btn.setFixedHeight(38)

            if item.get("type") == "Spacer":
                btn.setStyleSheet("""
                    QPushButton {
                        background-color: transparent;
                        border: 1px dashed #555555;
                        border-radius: 6px;
                    }
                    QPushButton:hover { background-color: #ff3b30; }
                """)
                btn.setText("Spacer")
                stretch = item.get("stretch", 1)
                self.preview_layout.addWidget(btn, stretch)
            else:
                btn.setStyleSheet("""
                    QPushButton {
                        background-color: #323232;
                        border: none;
                        border-radius: 6px;
                        color: #ffffff;
                    }
                    QPushButton:hover { background-color: #ff3b30; }
                """)
                val = item.get("val", "")
                if item.get("type") == "Icon":
                    if val.startswith("cupertino_"):
                        val = val[10:]
                    pixmap = self.get_icon_pixmap(val)
                    if pixmap:
                        btn.setIcon(QIcon(pixmap))
                        btn.setIconSize(QSize(24, 24))
                    else:
                        btn.setText(val)
                else:
                    btn.setText(val)

                self.preview_layout.addWidget(btn, item.get("stretch", 1))

            btn.clicked.connect(lambda checked, idx=i: self.remove_from_layout(idx))

    def load_active_config(self):
        # Prefer user local config if available
        user_config_dir = os.path.expanduser("~/.config/touchbar-enhancer")
        user_config_path = os.path.join(user_config_dir, "config.toml")

        config_path = user_config_path if os.path.exists(user_config_path) else "/etc/tiny-dfr/config.toml"

        if not os.path.exists(config_path):
            self.render_preview()
            return

        try:
            with open(config_path, "rb") as f:
                config = tomllib.load(f)

            media_default = config.get("MediaLayerDefault", True)
            self.settings["media_default"] = media_default
            self.settings["show_outlines"] = config.get("ShowButtonOutlines", True)
            self.settings["enable_pixel_shift"] = config.get("EnablePixelShift", False)
            self.settings["adaptive_brightness"] = config.get("AdaptiveBrightness", True)
            self.settings["font_template"] = config.get("FontTemplate", ":bold")

            if "MediaLayerKeys" in config:
                self.media_specs = self._parse_layer_config(config["MediaLayerKeys"])

            if "PrimaryLayerKeys" in config:
                self.primary_specs = self._parse_layer_config(config["PrimaryLayerKeys"])
            else:
                self.primary_specs = [
                    *[{"type": "Text", "val": f"F{i}", "action": f"F{i}", "stretch": 1} for i in range(1, 13)]
                ]

            self.layout_specs = self.media_specs if media_default else self.primary_specs

            self.layer_toggle.setChecked(self.settings["media_default"])
            self.chk_show_outlines.setChecked(self.settings["show_outlines"])
            self.chk_pixel_shift.setChecked(self.settings["enable_pixel_shift"])
            self.chk_adaptive_brightness.setChecked(self.settings["adaptive_brightness"])
            self.render_preview()

        except Exception as e:
            QMessageBox.warning(self, "Error", f"Error loading configuration: {e}")

    def _parse_layer_config(self, keys):
        layout = []
        for item_dict in keys:
            t_type = "Spacer"
            val = ""
            action = ""
            stretch = 1
            spacer_type = "flexible"

            if "Text" in item_dict:
                t_type = "Text"
                val = item_dict["Text"]
            elif "Icon" in item_dict:
                t_type = "Icon"
                val = item_dict["Icon"]
                if val.startswith("cupertino_"):
                    val = val[10:]
            elif "Time" in item_dict:
                t_type = "Time"
                val = item_dict["Time"]
            elif "Battery" in item_dict:
                t_type = "Battery"
                val = item_dict["Battery"]

            raw_act = item_dict.get("Action", "")
            if isinstance(raw_act, list):
                action = ", ".join(raw_act)
            else:
                action = str(raw_act)

            stretch = item_dict.get("Stretch", 1)

            if t_type == "Spacer":
                if stretch == 1:
                    spacer_type = "small"
                elif stretch == 2:
                    spacer_type = "large"
                else:
                    spacer_type = "flexible"

            layout.append({
                "type": t_type,
                "val": val,
                "action": action,
                "stretch": stretch,
                "spacer_type": spacer_type
            })
        return layout

    def deploy_config(self):
        try:
            self.settings["media_default"] = self.layer_toggle.isChecked()
            self.settings["show_outlines"] = self.chk_show_outlines.isChecked()
            self.settings["enable_pixel_shift"] = self.chk_pixel_shift.isChecked()
            self.settings["adaptive_brightness"] = self.chk_adaptive_brightness.isChecked()

            toml = build_config_toml(
                self.media_specs,
                self.primary_specs,
                media_layer_default=self.settings["media_default"],
                show_button_outlines=self.settings["show_outlines"],
                enable_pixel_shift=self.settings["enable_pixel_shift"],
                adaptive_brightness=self.settings["adaptive_brightness"],
                font_template=self.settings.get("font_template", ":bold")
            )

            secure_dir = tempfile.mkdtemp(prefix="touchbar_enhancer_")
            tmp_config_path = os.path.join(secure_dir, "config.toml")
            custom_icons_to_copy = []

            # We need to collect the custom icons used in the layout
            icons_needed = set()
            for specs in [self.media_specs, self.primary_specs]:
                for item in specs:
                    if item.get("type") == "Icon":
                        val = item.get("val", "")
                        if val.startswith("cupertino_"):
                            val = val[10:]
                        if val in CUPERTINO_ICONS_MAP and val not in TINY_DFR_BUILTIN_ICONS:
                            icons_needed.add(val)

            # Generate PNGs from font
            for name in icons_needed:
                pixmap = self.get_icon_pixmap(name, size=64)
                if pixmap:
                    tmp_png_path = os.path.join(secure_dir, f"cupertino_{name}.png")
                    pixmap.save(tmp_png_path, "PNG")
                    custom_icons_to_copy.append((tmp_png_path, f"/etc/tiny-dfr/cupertino_{name}.png"))

            # Save locally for GUI persistence
            user_config_dir = os.path.expanduser("~/.config/touchbar-enhancer")
            os.makedirs(user_config_dir, exist_ok=True)
            user_config_path = os.path.join(user_config_dir, "config.toml")
            with open(user_config_path, 'w', encoding='utf-8') as f:
                f.write(toml)

            with open(tmp_config_path, 'w', encoding='utf-8') as f:
                f.write(toml)

            script_path = os.path.join(secure_dir, "deploy-tiny-dfr.sh")
            script_lines = [
                '#!/bin/bash',
                'set -euo pipefail',
                'install -d /etc/tiny-dfr',
                'install -d /var/lib/touchbar-enhancer/icons',
            ]

            # Copy config to /var/lib/touchbar-enhancer for systemd restoration
            script_lines.append(f"install -m 0644 '{tmp_config_path}' '/var/lib/touchbar-enhancer/config.toml'")
            script_lines.append(f"install -m 0644 '{tmp_config_path}' '/etc/tiny-dfr/config.toml'")

            for src, dst in custom_icons_to_copy:
                script_lines.append(f"install -m 0644 '{src}' '{dst}'")
                # Also save icon to /var/lib for persistence
                icon_basename = os.path.basename(dst)
                script_lines.append(f"install -m 0644 '{src}' '/var/lib/touchbar-enhancer/icons/{icon_basename}'")

            # Create systemd drop-in
            dropin_dir = "/etc/systemd/system/tiny-dfr.service.d"
            dropin_file = f"{dropin_dir}/99-touchbar-enhancer.conf"
            script_lines.extend([
                f"install -d {dropin_dir}",
                "cat << 'EOF' > " + dropin_file,
                "[Service]",
                "ExecStartPre=-/usr/bin/mkdir -p /etc/tiny-dfr",
                "ExecStartPre=-/usr/bin/cp -f /var/lib/touchbar-enhancer/config.toml /etc/tiny-dfr/config.toml",
                "ExecStartPre=-/bin/sh -c 'cp -f /var/lib/touchbar-enhancer/icons/* /etc/tiny-dfr/ 2>/dev/null || true'",
                "EOF"
            ])

            script_lines.append('systemctl daemon-reload')
            script_lines.append('systemctl restart tiny-dfr')

            with open(script_path, 'w', encoding='utf-8') as f:
                f.write("\n".join(script_lines) + "\n")
            os.chmod(script_path, 0o755)

            exit_code = 1
            if hasattr(os, 'geteuid') and os.geteuid() == 0:
                completed = subprocess.run([script_path], capture_output=True, text=True, check=False)
                exit_code = completed.returncode
            elif shutil.which('pkexec'):
                completed = subprocess.run(['pkexec', script_path], capture_output=True, text=True, check=False)
                exit_code = completed.returncode
            else:
                QMessageBox.critical(self, "Error", "pkexec is not available. Install pkexec or run as root.")
                return

            if exit_code == 0:
                QMessageBox.information(self, "Success", "Configuration deployed successfully!")
            else:
                QMessageBox.critical(self, "Error", f"Failed with exit code {exit_code}.\n{completed.stderr}")

        except Exception as exc:
            QMessageBox.critical(self, "Error", str(exc))
        finally:
            if 'secure_dir' in locals() and os.path.exists(secure_dir):
                shutil.rmtree(secure_dir)

    def show_about(self):
        QMessageBox.about(self, "About Touch Bar Enhancer",
            "<h3>Touch Bar Enhancer</h3>"
            "<p>Version: Alpha</p>"
            '<p>Created by Julien.<br>'
            'GitHub: <a href="https://github.com/julien/touchbarv2">https://github.com/julien/touchbarv2</a></p>')

def main():
    # Fix for wayland display scaling on Qt
    os.environ["QT_QPA_PLATFORM"] = "wayland;xcb"

    app = QApplication(sys.argv)

    # Set modern fusion style
    app.setStyle("Fusion")

    # Load CupertinoIcons font
    font_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "icons", "CupertinoIcons.ttf")
    if os.path.exists(font_path):
        QFontDatabase.addApplicationFont(font_path)

    window = TouchbarEnhancer()
    window.show()

    sys.exit(app.exec())

if __name__ == '__main__':
    main()
