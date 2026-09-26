# AI Connection Template

This repository is a starting point for a native Windows desktop app that talks to an OpenAI-compatible API. It is not a finished product.

The window shows only the connection form at the top. **Reload** and **Save** stay inside that form. The space under it is empty on purpose. Add the rest of the product there.

The application name, icon, window size, and taskbar identity are set only in `config.json`. They are not on the form and cannot be changed from the interface.

## Run

```bash
pip install -r requirements.txt
python ai_connection_teamplate.py
```

Dependencies:

- `openai` (Apache-2.0) — OpenAI-compatible API client
- `PySide6` (LGPL-3.0) — native Windows UI

## What Save and Reload do

On startup the form reads `config.json`.

**Save** writes the four form fields back to the file:

- `api_key`
- `base_url`
- `model`
- `timeout_seconds`

Everything else in `config.json` is kept from the copy already in memory, including `window.title`, `window.icon`, size, and `app_user_model_id`.

**Reload** throws away unsaved form edits, reads the file again, and refreshes the form, the icon, and the application name.

If you edit `config.json` on disk while the window is open, press **Reload** before **Save**. Otherwise Save overwrites the file with the older in-memory copy.

Placeholder values such as `YOUR_API_KEY` are saved as written. The form does not call the API, so it does not treat them as errors.

## Form fields

| Field | `config.json` key | Meaning |
| --- | --- | --- |
| API key | `api_key` | Key sent to the API. Hidden until **Show key** is checked. |
| Base URL | `base_url` | Gateway address, including the port if it has one. |
| Model / agent | `model` | Model or agent name. |
| Timeout | `timeout_seconds` | How many seconds one API request may wait. Used only by `create_client()`, not by the form itself. |

## Application name

The visible name comes only from `window.title` in `config.json`. The code has no second copy, and the form has no field for it.

That value is used for:

- the window title bar
- the Qt application name

Change `window.title`, then press **Reload** or restart the app. **Save** from the form cannot rename the application.

If `config.json` cannot be read at startup, a dialog titled `Configuration error` is shown, because the name from the file is not available yet.

## Window settings (config only)

These live under `window` in `config.json`. Edit the file, not the form.

| Key | Meaning |
| --- | --- |
| `title` | Application name. Title bar and Qt name. |
| `width`, `height` | Window size in pixels. |
| `icon` | Path to the window and taskbar picture. |
| `app_user_model_id` | Windows taskbar identity. Change this when you reuse the template, so Windows does not group this app with another copy or with `python.exe`. |

Restart after changing `app_user_model_id`. Windows reads that id before the window opens.

## Icon

The template does not include an icon. `assets/` is only the usual place to put one.

`window.icon` is `assets/icon.png` by default. Two ways to set it:

1. Put your picture at `assets/icon.png` and leave the config value as it is.
2. Change `window.icon` to another path. A relative path starts from the application folder, not from the folder you launched the app in. An absolute path is used as written. PNG and ICO both work.

If the path is empty or the file is missing, the app still starts. The window and taskbar then use the normal Windows icon.

## Where to add your own UI

In `SettingsWindow._build_ui()` the connection group is added first. Under it there is an empty stretch. Insert new widgets above that stretch so they stay under the connection block and still grow with the window. Leave the connection group as it is.

## Calling the API

The form does not send requests. When later code needs a client, call `create_client()` and pass either `load_config()` or the dictionary from `SettingsWindow._collect()`.

```python
from ai_connection_teamplate import create_client, load_config

client = create_client(load_config())
```

`create_client()` uses `api_key`, `base_url`, and `timeout_seconds`. Do not call it on the UI thread for long requests.

## Files

- `ai_connection_teamplate.py` — window, config load/save, and `create_client()`
- `config.json` — connection values and window settings
- `requirements.txt` — Python packages
- `assets/` — optional folder for `icon.png` or any other file named by `window.icon`
