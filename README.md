# SbtDeskTran

Desktop translation app for **Windows 11** — no installation required.

## Requirements

- **Python 3.8+** (comes with Windows or download from python.org)
- No additional packages needed — uses Python standard library only

## Run

```bat
python main.py
```

or double-click `SbtDeskTran.bat`

## Build Standalone EXE

Double-click **`build.bat`** — it will:

1. Auto-install [PyInstaller](https://pyinstaller.org/) if not present
2. Generate `icon.ico` if missing
3. Compile everything into a single `dist\SbtDeskTran.exe`

```bat
build.bat
```

> Output: `dist\SbtDeskTran.exe` — no Python installation required to run.

To regenerate the icon only:

```bat
python create_icon.py
```

## Features

| Feature               | Details                                                                 |
| --------------------- | ----------------------------------------------------------------------- |
| **Translation**       | Google Translate (no API key) with auto-language detection              |
| **Layout**            | Horizontal (side-by-side) or Vertical (top-bottom) split                |
| **Compact Mode**      | Small minimal window, toggle with ▣ button                              |
| **Always on Top**     | Pin window above all others with 📌 button                              |
| **Diff Mode**         | Side-by-side diff of source vs translation with word-level highlighting |
| **Themes**            | Dark (Catppuccin-inspired) and Light                                    |
| **Auto-translate**    | Translates 500ms after you stop typing                                  |
| **Keyboard shortcut** | `Ctrl+Enter` to force translate immediately                             |

## Adding More Translation Engines

Edit `translator_engine.py` — add a new class with a `translate()` method and register it in `ENGINES`:

```python
class MyEngine:
    name = "My Engine"
    def translate(self, text, src="auto", dest="en") -> dict:
        # return {"translated": "...", "detected_lang": "en", "source": self.name}
        ...

ENGINES["My Engine"] = MyEngine()
```

## File Structure

```
translator/
  main.py              — Entry point
  app.py               — Main window & UI logic
  widgets.py           — FlatButton, DiffViewer widgets
  translator_engine.py — Translation backends
  diff_engine.py       — Line/word-level diff algorithm
  theme.py             — Dark & Light theme definitions
  settings.json        — Auto-saved user preferences (created on first run)
  icon.ico             — App icon (multi-resolution: 16–256px)
  create_icon.py       — Regenerate icon.ico (no extra deps needed)
  build.bat            — Build standalone dist\SbtDeskTran.exe via PyInstaller
  SbtDeskTran.bat      — Run with Python directly
```
