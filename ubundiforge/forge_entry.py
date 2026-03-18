"""Bootstrap entry point for the forge CLI.

This module is force-included into site-packages so it can be imported
directly by the console_scripts entry point — bypassing the broken .pth
file that uv generates for editable installs (Python 3.12+ skips .pth
files starting with '_').
"""

import os
import sys


def main() -> None:
    # Find the project root from the .pth file uv created
    site_packages = os.path.dirname(os.path.abspath(__file__))
    pth_file = os.path.join(site_packages, "_ubundiforge.pth")

    if os.path.exists(pth_file):
        project_root = open(pth_file).read().strip()
        if project_root and project_root not in sys.path:
            sys.path.insert(0, project_root)

    from ubundiforge.cli import app

    raise SystemExit(app())
