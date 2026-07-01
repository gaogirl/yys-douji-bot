# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

阴阳师斗技自动挂机 — a Windows GUI automation tool for the game Onmyoji (阴阳师) that automates the PvP arena (斗技) workflow. Built with Python 3.8+ on Windows only.

## Architecture

```
main.py (Tkinter GUI, DoujiApp)
 ├── config.py                          # Central constants (templates, regions, anti-detect, stats)
 ├── window_manager.py                  # Win32 window enumeration, PrintWindow screenshot
 ├── image_recognition.py               # OpenCV template matching (TM_CCOEFF_NORMED)
 ├── auto_clicker.py                    # Smooth mouse movement (Bezier curve) + click with anti-detect randomization
 ├── douji_bot.py                       # State machine driving the automation loop
 │    ├── battle_stats.py               # Win/loss tracking, session timing, JSON persistence
 │    ├── team_manager.py               # Multi-team CRUD, JSON persistence
 │    └── selection_handler.py          # Auto-select shikigami via clipboard search + drag
 ├── hotkey_manager.py                  # F6 toggle via GetAsyncKeyState polling
 └── tray_manager.py                    # pystray system tray (minimize to tray on close)
```

**Core flow:** `DoujiApp` wires all modules together and passes them to `DoujiBot`. The bot runs a threaded state machine (`FIND_MATCH → SELECTING → AUTO_SELECT → IN_BATTLE → BATTLE_END`), repeatedly screenshotting the game window, matching UI elements via OpenCV template matching, and clicking results through the anti-detect auto-clicker.

**Anti-detection:** Mouse movement uses quadratic Bezier curves with random midpoints. Click positions, durations, and delays are randomized. Scan intervals have jitter. All controlled via `ANTI_DETECT` dict in `config.py`.

## Key Files

| File | Purpose |
|------|---------|
| `main.py` | Tkinter GUI entry point. All user controls wired here. |
| `config.py` | Single source of truth: template filenames, window keywords, confidence thresholds, anti-detect params, hotkey mapping. |
| `douji_bot.py` | State machine — the brain. `_run_loop` is the main automation loop. |
| `image_recognition.py` | OpenCV `matchTemplate` wrapper. Templates loaded once at init. |
| `auto_clicker.py` | Win32 mouse simulation with bezier smoothing and randomization. |
| `window_manager.py` | `EnumWindows` + `PrintWindow` for reliable window screenshot. |
| `selection_handler.py` | Clipboard-based search for auto-picking shikigami. |
| `team_manager.py` | JSON-backed multi-team storage. |
| `battle_stats.py` | Session/permanent win/loss stats, persisted to `stats.json`. |
| `hotkey_manager.py` | Polling-based global F6 toggle (no Win32 hotkey registration). |
| `tray_manager.py` | pystray system tray icon for minimize-to-tray behavior. |

## Commands

**Run (development):**
```bash
pip install -r requirements.txt
python main.py
```

**Package (release):**
```bash
build.bat
# or manually:
pyinstaller --noconfirm --windowed --onefile ^
    --name "阴阳师斗技自动挂机" ^
    --add-data "templates;templates" ^
    --hidden-import=win32gui --hidden-import=win32ui ^
    --hidden-import=psutil --hidden-import=pystray ^
    --collect-all pystray main.py
```

Output: `dist/阴阳师斗技自动挂机.exe` (+ `dist/templates/` with screenshot assets).

## Dependencies

- `pywin32` — Win32 window/screenshot/mouse control
- `opencv-python` — Template matching
- `numpy` — Image array manipulation
- `Pillow` — Tray icon image
- `psutil` — Process name lookup for window validation
- `pystray` — System tray icon
- `pyinstaller` — One-file packaging

## Important Notes

- **Windows-only**: Uses `win32gui`, `win32ui.PrintWindow`, `win32api.GetAsyncKeyState` — will not run on other platforms.
- **Template images** in `templates/` must match the game's resolution. Users capture them manually per README.md.
- **No tests exist** in this project. Manual testing is the intended workflow.
- **Thread safety**: `DoujiBot` runs in a daemon thread; GUI callbacks use `root.after(0, ...)` for thread-safe Tkinter updates.
- **Configuration is code-only** — there is no settings dialog. Adjust `config.py` constants or use the GUI sliders (confidence only).
