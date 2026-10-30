"""
launcher.py: PyInstaller entry script
"""

import sys

from ocmp.__main__ import main

if __name__ == "__main__":
    sys.exit(main())
