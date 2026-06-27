"""Windowed test — quick visual launch using multi-backend launcher."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

if __name__ == "__main__":
    args = ["--render", "nova"] + sys.argv[1:]
    sys.argv = ["launcher.py"] + args
    from render.launcher import main
    main()
