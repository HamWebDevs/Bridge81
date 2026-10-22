"""Real Tk smoke check: run with a desktop display, outside unittest discovery."""

import json
import sys
import tempfile
import time
from unittest import mock
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import tkinter as tk

from bridge81.gui import App
from helpers import game


def main():
    with tempfile.TemporaryDirectory(prefix="Bridge81 GUI ") as directory:
        # Windows temp paths can use 8.3 aliases. The log reader intentionally
        # rejects noncanonical paths, so use the real disposable fixture path.
        folder = Path(directory).resolve()
        script = folder / "hello world.py"
        script.write_text("import sys,json; print(json.dumps(sys.argv[1:]))\n")
        root = tk.Tk()
        root.withdraw()
        app = App(root)
        def unexpected_error(error):
            raise AssertionError("Unexpected GUI error: " + str(error))
        # Unexpected errors must fail CI instead of blocking on a modal dialog.
        app.fail = unexpected_error
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
            app.inspect_dependencies()
            assert "Static direct/delay-import evidence" in app.game_output.get("1.0", "end")
            assert "1 modules, 0 imports" in app.status.get()
            app.profile.set("low-memory")
            app.game_action(False)
            assert "RENPY_LESS_MEMORY" in app.game_output.get("1.0", "end")
            log = folder / 'private-runtime.txt'
            log.write_text('C:\\Users\\PRIVATE_PERSON\\game\\secret.py\nWinError 126: specified module could not be found\n', encoding='utf-8')
            with mock.patch('tkinter.filedialog.askopenfilename', return_value=str(log)):
                app.inspect_runtime_log()
            assert 'loader-module-missing' in app.game_output.get('1.0', 'end')
            assert 'PRIVATE_PERSON' not in app.game_output.get('1.0', 'end')
            original = log.read_text()
            with mock.patch('tkinter.filedialog.askopenfilename', return_value=''):
                app.inspect_runtime_log()
            assert app.runtime_log_path == log
            assert log.read_text() == original
            log.write_text('PRIVATE_PERSON\nWinError 193: not a valid Win32 application\n', encoding='utf-8')
            export = folder / 'log-hints.json'
            with mock.patch('tkinter.filedialog.asksaveasfilename', return_value=str(export)):
                app.export_runtime_log()
            saved = json.loads(export.read_text(encoding='utf-8'))
            assert saved['findings'][0]['code'] == 'loader-architecture', 'Export used stale log evidence'
            assert 'PRIVATE_PERSON' not in export.read_text(encoding='utf-8')
            with mock.patch('tkinter.filedialog.asksaveasfilename', return_value=str(export)), mock.patch.object(app, 'fail') as failed:
                app.export_runtime_log()
                failed.assert_called_once()
            assert json.loads(export.read_text(encoding='utf-8')) == saved
            with mock.patch('tkinter.filedialog.asksaveasfilename', return_value=str(log)), mock.patch.object(app, 'fail') as failed:
                app.export_runtime_log()
                failed.assert_called_once()
            assert 'WinError 193' in log.read_text()
            with mock.patch('tkinter.filedialog.askopenfilename', return_value=str(folder / 'missing.log')), mock.patch.object(app, 'fail'):
                app.inspect_runtime_log()
            assert app.runtime_log_path is None
            assert str(app.export_log_button.cget('state')) == 'disabled'
            app.tabs.select(app.game_tab)
            root.deiconify()
            for width in (1000, 780):
                root.geometry(str(width) + 'x660')
                root.update()
                def descendants(widget):
                    for child in widget.winfo_children():
                        yield child
                        yield from descendants(child)
                buttons = [w for w in descendants(app.game_tab) if w.winfo_class() == 'TButton'
                           and w.cget('text') in {'Inspect game', 'Inspect DLLs', 'Preview launch', 'Launch game', 'Export report', 'Read saved log…', 'Save log hints…'}]
                assert len(buttons) == 7
                for button in buttons:
                    assert button.winfo_ismapped() and button.winfo_x() + button.winfo_width() <= button.master.winfo_width(), button.cget('text')
            root.update()
            print("GUI smoke passed: widgets, background run, game/DLL inspection, private saved-log inspection/export/cancellation/freshness/collision checks and small-window layout.")
        finally:
            root.destroy()


if __name__ == "__main__":
    main()
