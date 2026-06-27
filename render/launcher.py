#!/usr/bin/env python3
"""
Karin Renderer Launcher — Nova backend entry point.

Usage:
    python -m render.launcher "model.glb"
    python -m render.launcher --toon "model.glb"
    python -m render.launcher --config render_config.json
"""
import argparse
import logging
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from render.backends import list_backends, create_backend
from render.config import RendererConfig


def main():
    parser = argparse.ArgumentParser(description="Karin VTuber Renderer — Multi-backend launcher")
    parser.add_argument("model", nargs="?", default=None, help="Path to .glb/.vrm/.pmx model file")
    parser.add_argument("--render", "-r", default="nova", choices=list_backends(),
                        help=f"Render backend to use (default: nova). Available: {', '.join(list_backends())}")
    parser.add_argument("--config", "-c", default=None, help="Path to render_config.json")
    parser.add_argument("--toon", "-t", action="store_true", help="Enable toon shading mode")
    parser.add_argument("--window-width", type=int, default=1280, help="Window width")
    parser.add_argument("--window-height", type=int, default=720, help="Window height")
    parser.add_argument("--list-backends", "-l", action="store_true", help="List available backends and exit")
    parser.add_argument("--api", default=None,
                        help="Graphics API to use (D3D12, Vulkan, Metal, OpenGL, DirectX 11)")
    parser.add_argument("--render-mode", default=None,
                        choices=["cpu", "gpu-hw", "cpu+gpu", "software"],
                        help="Render mode: cpu solo, gpu via hardware, cpu+gpu, via software")
    parser.add_argument("--dance", default=None, help="Path to extracted dance JSON file")
    parser.add_argument("--debug", "-d", action="store_true", help="Enable debug logging")

    args = parser.parse_args()

    if args.list_backends:
        print("Available render backends:")
        for name in list_backends():
            print(f"  {name}")
        return

    level = logging.DEBUG if args.debug else logging.INFO
    logging.basicConfig(level=level, format="%(name)s: %(levelname)s: %(message)s")

    config = RendererConfig()
    if args.config:
        config = RendererConfig.load(args.config)

    if args.toon:
        config.toon_mode = True

    if args.model:
        config.model_path = args.model

    config.window_width = args.window_width
    config.window_height = args.window_height

    if args.api:
        config.render_api = args.api

    if args.render_mode:
        config.render_mode = args.render_mode

    if args.dance:
        config.video_dance_path = args.dance

    print(f"Karin VTuber Renderer — Backend: {args.render}")
    print(f"  Model: {config.model_path or '(none)'}")
    print(f"  Toon mode: {config.toon_mode}")
    if args.api:
        print(f"  API: {args.api}")

    backend = create_backend(args.render, config=config)

    try:
        backend.run()
    except KeyboardInterrupt:
        print("\nShutting down...")
    finally:
        backend.shutdown()


if __name__ == "__main__":
    main()
