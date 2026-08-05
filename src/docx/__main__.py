"""Entry point for `python -m docx`.

The command surface itself is in :mod:`docx.cli`; this is only the hook that makes
``python -m docx`` reach it.
"""

from __future__ import annotations

import sys

from docx.cli import main

if __name__ == "__main__":
    sys.exit(main())
