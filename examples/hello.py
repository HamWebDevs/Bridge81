"""Use this file for your first Bridge81 Python run."""

import json
import platform
import sys

print("Hello from Bridge81!")
print("Python:", platform.python_version())
print("Arguments:", json.dumps(sys.argv[1:], ensure_ascii=False))
print("Try making a venv, then choose its Scripts/python.exe for your project.")
