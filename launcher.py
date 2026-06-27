#!/usr/bin/env python3
"""Karin Renderer — Nova VTuber render engine.
Usage:
    python launcher.py "model.glb"
    python launcher_ui.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from render.launcher import main
if __name__ == "__main__":
    main()
