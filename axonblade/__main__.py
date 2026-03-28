"""
axonblade/__main__.py — entry point for the `ablade` CLI command.
Delegates to main.py at the project root.
"""

import sys
import os

# Ensure the project root is on the path so core/, stdlib/, grid/ are importable
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from main import main  # noqa: E402

if __name__ == "__main__":
    main()
