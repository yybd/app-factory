#!/usr/bin/env python3
"""Turn on the right tracks for one repo — a shim; the tool lives in the plugin.

    cd <your app repo>
    python3 <app-factory>/factory/enable.py --yes

The real file is `plugins/factory-setup/scripts/enable.py`, because that is the copy
that reaches a machine. A marketplace added from a directory keeps that directory, but
one added from GitHub is cloned into `~/.claude/plugins/marketplaces/app-factory/` and
installs each plugin into `~/.claude/plugins/cache/` — so a reader told to run
`factory/enable.py` had a path that existed only for whoever wrote the sentence.

This shim stays because the documentation, the READMEs and two years of muscle memory
point at it. It runs the other file in-process, so `--help` and every exit code are
the real ones.
"""
import os
import runpy
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REAL = os.path.join(os.path.dirname(HERE), "plugins", "factory-setup", "scripts", "enable.py")

if not os.path.isfile(REAL):
    sys.exit(f"✗ {REAL} is missing — this shim has nothing to run.")
sys.argv[0] = REAL
runpy.run_path(REAL, run_name="__main__")
