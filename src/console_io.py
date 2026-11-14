"""In log an toàn trên Windows (tránh UnicodeEncodeError cp1252)."""

from __future__ import annotations

import sys


def ensure_utf8_stdio() -> None:
    for stream in (sys.stdout, sys.stderr):
        if stream is None:
            continue
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is None:
            continue
        try:
            reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass


def safe_print(*parts: object, file=None) -> None:
    ensure_utf8_stdio()
    target = file if file is not None else sys.stdout
    text = " ".join(str(p) for p in parts)
    try:
        print(text, file=target)
    except UnicodeEncodeError:
        enc = getattr(target, "encoding", None) or "utf-8"
        data = (text + "\n").encode(enc, errors="replace")
        buffer = getattr(target, "buffer", None)
        if buffer is not None:
            buffer.write(data)
            buffer.flush()
        else:
            print(text.encode(enc, errors="replace").decode(enc, errors="replace"), file=target)
