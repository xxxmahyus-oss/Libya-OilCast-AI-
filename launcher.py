"""Desktop launcher for Libya OilCast AI (Streamlit + pywebview)."""

import os
import socket
import sys
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path

import webview
from streamlit.web import cli as stcli

APP_TITLE = "Libya OilCast AI"

if getattr(sys, "frozen", False):
    APP_PATH = Path(getattr(sys, "_MEIPASS")) / "app.py"
else:
    APP_PATH = Path(__file__).resolve().with_name("app.py")


def _find_free_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def _start_streamlit(port):
    os.environ["STREAMLIT_SERVER_HEADLESS"] = "true"
    os.environ["STREAMLIT_BROWSER_GATHER_USAGE_STATS"] = "false"
    stcli.main(
        args=[
            "run",
            str(APP_PATH),
            "--server.address=127.0.0.1",
            f"--server.port={port}",
            "--server.headless=true",
            "--server.fileWatcherType=none",
            "--browser.gatherUsageStats=false",
        ],
        prog_name="streamlit",
        standalone_mode=False,
    )


def _show_error(message):
    try:
        import tkinter as tk
        from tkinter import messagebox

        root = tk.Tk()
        root.withdraw()
        messagebox.showerror(APP_TITLE, message)
        root.destroy()
    except Exception:
        print(message, file=sys.stderr)


def main():
    if not APP_PATH.is_file():
        _show_error(f"لم يتم العثور على ملف البرنامج:\n{APP_PATH}")
        return 1

    port = _find_free_port()
    server_thread = threading.Thread(
        target=_start_streamlit,
        args=(port,),
        name="OilCast-Streamlit",
        daemon=True,
    )
    server_thread.start()

    url = f"http://127.0.0.1:{port}"
    ready = False
    for _ in range(90):
        if not server_thread.is_alive():
            break
        try:
            with urllib.request.urlopen(url, timeout=1) as response:
                if response.status < 500:
                    ready = True
                    break
        except (urllib.error.URLError, TimeoutError, OSError):
            time.sleep(1)

    if not ready:
        _show_error(
            "تعذر تشغيل خادم البرنامج المحلي.\n"
            "أغلق البرنامج وافتحه مرة أخرى. إذا تكررت المشكلة، "
            "أرسل صورة رسالة الخطأ."
        )
        return 1

    webview.create_window(
        APP_TITLE,
        url,
        width=1450,
        height=930,
        min_size=(1050, 700),
    )
    webview.start(debug=False)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
