import os
import sys

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
API_DIR = os.path.join(ROOT_DIR, "api")

if API_DIR not in sys.path:
    sys.path.insert(0, API_DIR)

from App import app, handler

__all__ = ["app", "handler"]
