"""Real Tk smoke check: run with a desktop display, outside unittest discovery."""

import json
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import tkinter as tk

from bridge81.gui import App
from helpers import game


def main():
    with tempfile.TemporaryDirectory(prefix="Bridge81 GUI ") as directory:
        folder = Path(directory)
        script = folder / "hello world.py"
        script.write_text("import sys,json; print(json.dumps(sys.argv[1:]))\n")
        root = tk.Tk()
        root.withdraw()
        app = App(root)
        try:
            app.script.set(str(script))
            app.script_args.set('["two words", "$(not-a-command)"]')
            app.preview_script()
            preview = json.loads(app.script_output.get("1.0", "end"))
            assert preview["argv"][-2:] == ["two words", "$(not-a-command)"]
            app.run_script()
            deadline = time.monotonic() + 10
            while app.busy and time.monotonic() < deadline:
                root.update()
                time.sleep(0.01)
            assert not app.busy, "GUI worker did not complete"
            assert '["two words", "$(not-a-command)"]' in app.script_output.get("1.0", "end")
            assert "completed" in app.status.get()
            app.folder.set(str(game(folder / "Story")))
            app.inspect_game()
            assert app.last_report.engine_version == (8, 3, 7)
            assert "unverified" in app.game_output.get("1.0", "end")
            assert hasattr(app, "repair_runtime")
            app.profile.set("low-memory")
            app.game_action(False)
            assert "RENPY_LESS_MEMORY" in app.game_output.get("1.0", "end")
            root.update()
            print("GUI smoke passed: widgets, preview, background run, game inspection and launch preview.")
        finally:
            root.destroy()


if __name__ == "__main__":
    main()
