"""
Điểm vào khi build .exe (PyInstaller).

  ToolClick.exe                 → cửa sổ app (tkinter)
  ToolClick.exe --toolclick-main ...  → worker (main.py CLI)
  ToolClick.exe --open-browser        → warmup Chrome
  ToolClick.exe --streamlit           → UI cũ trên trình duyệt (tuỳ chọn)
"""

from __future__ import annotations

import os
import sys


def _run_cli() -> None:
    from toolclick_paths import ensure_runtime_layout, writable_root

    ensure_runtime_layout()
    os.chdir(writable_root())
    sys.argv = [a for a in sys.argv if a != "--toolclick-main"]
    if not sys.argv:
        sys.argv = ["toolclick"]
    elif sys.argv[0].endswith("ToolClick.exe") or sys.argv[0].endswith("toolclick_entry"):
        sys.argv[0] = "toolclick"
    from main import main

    main()


def _run_desktop() -> None:
    from toolclick_paths import ensure_runtime_layout, writable_root

    ensure_runtime_layout()
    os.chdir(writable_root())
    try:
        from desktop_app import main as desktop_main

        desktop_main()
    except Exception:
        import traceback

        err = writable_root() / "toolclick_error.log"
        err.write_text(traceback.format_exc(), encoding="utf-8")
        raise


def _run_streamlit() -> None:
    from toolclick_paths import ensure_runtime_layout, resource_root, writable_root

    ensure_runtime_layout()
    os.chdir(writable_root())
    app = resource_root() / "streamlit_app.py"
    if not app.is_file():
        print(f"Không tìm thấy {app}", file=sys.stderr)
        sys.exit(1)

    port = os.environ.get("TOOLCLICK_PORT", "8501")
    os.environ.setdefault("STREAMLIT_GLOBAL_DEVELOPMENT_MODE", "false")
    sys.argv = [
        "streamlit",
        "run",
        str(app),
        "--global.developmentMode",
        "false",
        "--server.headless",
        "true",
        "--browser.gatherUsageStats",
        "false",
        "--server.port",
        port,
        "--server.address",
        "localhost",
    ]
    from streamlit.web import cli as stcli

    print(f"ToolClick UI: http://localhost:{port}")
    stcli.main()


def _run_open_browser() -> None:
    from toolclick_paths import ensure_runtime_layout, writable_root

    ensure_runtime_layout()
    os.chdir(writable_root())
    from open_browser import main as open_browser_main

    open_browser_main()


if __name__ == "__main__":
    if "--toolclick-main" in sys.argv:
        _run_cli()
    elif "--open-browser" in sys.argv:
        _run_open_browser()
    elif "--streamlit" in sys.argv:
        _run_streamlit()
    else:
        _run_desktop()
