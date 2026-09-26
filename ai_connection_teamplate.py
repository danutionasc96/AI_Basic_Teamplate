"""
AI connection template for a native Windows desktop app.

This file is the starting point, not a finished product. It opens one
window with the connection form at the top. The space under that form is
empty so later work can be added there.

What the form edits (Save writes only these keys):
- api_key
- base_url
- model
- timeout_seconds

What stays in config.json and is not on the form:
- window.title — application name (title bar and Qt name)
- window.width, window.height — window size
- window.icon — path to the window and taskbar picture
- window.app_user_model_id — Windows taskbar identity

How Save works:
- Reads the four form fields.
- Starts from the config already in memory (loaded at startup or Reload).
- Replaces only those four keys, then rewrites the whole file.
- Title, icon, size, and taskbar id are kept as they were in memory.
- If you edited config.json on disk while the window was open, press
  Reload before Save, or those disk edits will be overwritten.

How to continue:
- Add widgets in SettingsWindow._build_ui(), after the connection group.
- Call create_client() when later code needs to talk to the API.
"""

from __future__ import annotations

import ctypes
import json
import sys
from pathlib import Path

from openai import OpenAI
from PySide6.QtCore import Qt
from PySide6.QtGui import QCloseEvent, QFont, QIcon
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QStyleFactory,
    QVBoxLayout,
    QWidget,
)


# Folder that contains this script, not the folder the user started it from.
# Relative paths in config.json, such as assets/icon.png, are resolved from here.
APP_DIR = Path(__file__).resolve().parent
CONFIG_PATH = APP_DIR / "config.json"

# Windows groups taskbar buttons by this id. Without it, the button often
# shows the python.exe icon instead of the file named by window.icon.
# Replace window.app_user_model_id in config.json when reusing the template.
DEFAULT_APP_USER_MODEL_ID = "template.ai.connection"


def load_config() -> dict:
    """Read config.json and return it as a dictionary.

    Called when the window opens and when the user presses Reload.
    Raises FileNotFoundError if the file is missing, and json.JSONDecodeError
    if the file is not valid JSON.
    """
    if not CONFIG_PATH.exists():
        raise FileNotFoundError(f"Missing configuration file: {CONFIG_PATH}")
    with CONFIG_PATH.open(encoding="utf-8") as f:
        return json.load(f)


def save_config(data: dict) -> None:
    """Replace config.json with the given dictionary.

    The whole file is rewritten. Call this with the dict from _collect(),
    which already keeps window and any other keys the form does not edit.
    """
    with CONFIG_PATH.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")


def window_settings(config: dict) -> dict:
    """Return the window object from config.

    Returns an empty dictionary when the key is missing or is not an object,
    so later lookups can use .get() without an extra check.
    """
    window = config.get("window")
    return window if isinstance(window, dict) else {}


def application_name(config: dict) -> str:
    """Return the application name from window.title in config.json.

    That key is the only source. The form has no name field, and this
    function does not fall back to a hard-coded string. Change the name
    in config.json, then restart or press Reload.
    """
    return str(window_settings(config).get("title", "")).strip()


def resolve_config_path(value: str) -> Path:
    """Turn a path written in config.json into a full path.

    An absolute path is used as written. A relative path, such as
    assets/icon.png, is joined to APP_DIR. This matters because the app may
    be started from another folder, and a relative path would otherwise
    point at the wrong place.
    """
    path = Path(value)
    if path.is_absolute():
        return path
    return (APP_DIR / path).resolve()


def icon_path_from_config(config: dict) -> Path | None:
    """Return the icon path from window.icon.

    Returns None when the key is missing or blank, so the window can open
    with no custom icon instead of failing.
    """
    raw = str(window_settings(config).get("icon", "")).strip()
    if not raw:
        return None
    return resolve_config_path(raw)


def load_app_icon(config: dict) -> QIcon:
    """Load the image named by window.icon.

    The usual path is assets/icon.png. The template does not ship a file.
    Put your own PNG or ICO there, or set window.icon to any other relative
    or absolute path. A missing path or a missing file returns an empty
    icon. The window still opens with the default Windows picture.
    """
    path = icon_path_from_config(config)
    if path is None or not path.is_file():
        return QIcon()
    return QIcon(str(path))


def apply_taskbar_identity(config: dict) -> None:
    """Make the Windows taskbar use this app icon, not the Python icon.

    The program is started with python.exe, so Windows would otherwise show
    the Python icon and group this window with other Python programs.
    Sets the AppUserModelID from window.app_user_model_id before any window
    is created. Changing the id later needs a restart to take effect.
    On other operating systems this function does nothing.
    """
    if sys.platform != "win32":
        return
    app_id = str(window_settings(config).get("app_user_model_id", "")).strip()
    if not app_id:
        app_id = DEFAULT_APP_USER_MODEL_ID
    set_app_id = ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID
    set_app_id.argtypes = [ctypes.c_wchar_p]
    set_app_id.restype = ctypes.HRESULT
    set_app_id(app_id)


def create_client(settings: dict) -> OpenAI:
    """Build the API client from the connection dictionary.

    This form does not call the API. Later code should call this function
    when it needs to send a request. Pass load_config() or the dictionary
    from SettingsWindow._collect().

    timeout_seconds is the maximum wait, in seconds, for one API response.
    If the server does not answer in time, the OpenAI library raises an error.
    The form itself does not use this value.
    """
    return OpenAI(
        api_key=settings["api_key"],
        base_url=settings["base_url"],
        timeout=settings.get("timeout_seconds", 90),
    )


class SettingsWindow(QMainWindow):
    """The application window.

    The top group is the connection form. Reload and Save stay inside it
    so they do not slide to the bottom when the window grows.
    Add later UI under that group in _build_ui(), above the empty stretch.
    """

    def __init__(self) -> None:
        super().__init__()
        self.config_data = load_config()
        window = window_settings(self.config_data)

        self._apply_application_name()
        self.resize(int(window.get("width", 480)), int(window.get("height", 320)))
        self.setMinimumSize(420, 280)

        self._build_ui()
        self._fill_from_config()
        self._apply_icon()
        self.statusBar().showMessage(f"Loaded {CONFIG_PATH.name}.")

    def _build_ui(self) -> None:
        # QMainWindow creates a menu bar even when we add no menus.
        # Hide it so the window shows only the form.
        self.menuBar().hide()

        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(10)

        # Keep fields, Reload, and Save inside this one group.
        # New interface code belongs after root.addWidget(connection), not here.
        connection = QGroupBox("AI Connection")
        connection_layout = QVBoxLayout(connection)
        connection_layout.setSpacing(8)

        form = QFormLayout()
        form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        form.setHorizontalSpacing(12)
        form.setVerticalSpacing(8)

        self.api_key_edit = QLineEdit()
        self.api_key_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.api_key_edit.setPlaceholderText("YOUR_API_KEY")
        form.addRow("API key", self.api_key_edit)

        self.show_key_check = QCheckBox("Show key")
        self.show_key_check.toggled.connect(self._toggle_key_visibility)
        form.addRow("", self.show_key_check)

        self.base_url_edit = QLineEdit()
        self.base_url_edit.setPlaceholderText("YOUR_BASE_URL")
        form.addRow("Base URL", self.base_url_edit)

        self.model_edit = QLineEdit()
        self.model_edit.setPlaceholderText("YOUR_AGENT_NAME")
        form.addRow("Model / agent", self.model_edit)

        # Saved as timeout_seconds. Used only by create_client(), not by this form.
        self.timeout_spin = QSpinBox()
        self.timeout_spin.setRange(1, 3600)
        self.timeout_spin.setSuffix(" s")
        form.addRow("Timeout", self.timeout_spin)
        connection_layout.addLayout(form)

        button_row = QHBoxLayout()
        button_row.addStretch(1)
        self.reload_btn = QPushButton("Reload")
        self.reload_btn.clicked.connect(self._reload)
        self.save_btn = QPushButton("Save")
        self.save_btn.setDefault(True)
        self.save_btn.clicked.connect(self._save)
        button_row.addWidget(self.reload_btn)
        button_row.addWidget(self.save_btn)
        connection_layout.addLayout(button_row)
        root.addWidget(connection)

        # Pushes the connection group to the top and leaves the rest empty.
        # Insert new widgets above this stretch so they sit under the form
        # and still grow with the window.
        root.addStretch(1)

    def _fill_from_config(self) -> None:
        """Put the values from self.config_data into the form fields.

        Called on startup and after Reload. A bad timeout value falls back
        to 90 seconds instead of crashing the window.
        """
        self.api_key_edit.setText(str(self.config_data.get("api_key", "")))
        self.base_url_edit.setText(str(self.config_data.get("base_url", "")))
        self.model_edit.setText(str(self.config_data.get("model", "")))
        timeout = self.config_data.get("timeout_seconds", 90)
        try:
            timeout_value = int(timeout)
        except (TypeError, ValueError):
            timeout_value = 90
        self.timeout_spin.setValue(timeout_value)

    def _collect(self) -> dict:
        """Read the form and return a full config dictionary.

        Starts from the dictionary already in memory, then replaces only
        api_key, base_url, model, and timeout_seconds.
        window.title, icon, size, and app_user_model_id are not on the form,
        so they are copied through unchanged.
        """
        data = dict(self.config_data)
        data["api_key"] = self.api_key_edit.text().strip()
        data["base_url"] = self.base_url_edit.text().strip()
        data["model"] = self.model_edit.text().strip()
        data["timeout_seconds"] = int(self.timeout_spin.value())
        return data

    def _save(self) -> None:
        """Write the four form fields into config.json.

        The rest of the file, including window settings, is kept from the
        in-memory copy. On a disk error, a dialog is shown and the file
        is not treated as saved.
        """
        self.config_data = self._collect()
        try:
            save_config(self.config_data)
        except OSError as extra:
            QMessageBox.critical(self, "Save failed", str(extra))
            self.statusBar().showMessage("Save failed.")
            return
        self.statusBar().showMessage(f"Saved {CONFIG_PATH.name}.")

    def _reload(self) -> None:
        """Throw away unsaved form edits and load config.json again.

        Also refreshes the icon and the application name, because those
        keys live only in the file and may have changed since startup.
        """
        try:
            self.config_data = load_config()
        except (OSError, json.JSONDecodeError) as extra:
            QMessageBox.critical(self, "Reload failed", str(extra))
            self.statusBar().showMessage("Reload failed.")
            return
        self._fill_from_config()
        self._apply_icon()
        self._apply_application_name()
        self.statusBar().showMessage(f"Reloaded {CONFIG_PATH.name}.")

    def _apply_application_name(self) -> None:
        """Set the title bar and the Qt application name from window.title.

        The form never writes this key, so Save cannot rename the app.
        """
        name = application_name(self.config_data)
        self.setWindowTitle(name)
        application = QApplication.instance()
        if application is not None:
            application.setApplicationName(name)
            application.setApplicationDisplayName(name)

    def _apply_icon(self) -> None:
        """Apply window.icon to this window and to the Qt application.

        If the file is missing, the default Windows icon is used. A missing
        file is not an error that stops the app.
        """
        icon = load_app_icon(self.config_data)
        self.setWindowIcon(icon)
        application = QApplication.instance()
        if application is not None:
            application.setWindowIcon(icon)
        path = icon_path_from_config(self.config_data)
        if path is not None and not path.is_file():
            self.statusBar().showMessage(f"Icon file not found: {path}")

    def _toggle_key_visibility(self, checked: bool) -> None:
        """Show or hide the API key.

        The key is hidden by default so it is not readable over the shoulder.
        Checking Show key switches the field to normal text.
        """
        mode = QLineEdit.EchoMode.Normal if checked else QLineEdit.EchoMode.Password
        self.api_key_edit.setEchoMode(mode)

    def closeEvent(self, event: QCloseEvent) -> None:  # noqa: N802 — Qt API
        super().closeEvent(event)


def native_windows_style() -> str:
    """Choose a built-in Windows look, with no custom colors.

    Tries windows11 first, then the older Windows styles.
    Fusion is only used when none of those exist, so the window still opens.
    """
    available = set(QStyleFactory.keys())
    for name in ("windows11", "Windows", "windowsvista"):
        if name in available:
            return name
    return "Fusion"


def main() -> int:
    """Start the application.

    Order matters:
    1. Read config.json. If that fails, show the error and stop.
    2. Set the Windows taskbar id before any window exists.
    3. Create the Qt application, apply the native style and the icon.
    4. Show the settings window and run until the user closes it.
    """
    try:
        config = load_config()
    except (OSError, json.JSONDecodeError, FileNotFoundError) as extra:
        app = QApplication(sys.argv)
        # config.json could not be read, so window.title is not available.
        QMessageBox.critical(None, "Configuration error", str(extra))
        return app.exec()
    apply_taskbar_identity(config)
    app = QApplication(sys.argv)
    app.setStyle(native_windows_style())
    app.setFont(QFont("Segoe UI", 9))
    app.setApplicationName(application_name(config))
    app.setApplicationDisplayName(application_name(config))
    app.setWindowIcon(load_app_icon(config))
    window = SettingsWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
