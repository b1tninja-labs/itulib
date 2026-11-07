"""`python -m itulib` is the same as the `itulib` command."""

from __future__ import annotations

from .cli import main

if __name__ == "__main__":
    raise SystemExit(main())
