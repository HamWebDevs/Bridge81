"""Real Windows/Cygwin integration, invoked by the dedicated CI job."""

import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from bridge81.plans import bash_plan
from bridge81.runner import run


def main():
    bash = os.environ.get("BRIDGE81_TEST_CYGWIN", "")
    if os.name != "nt" or not Path(bash).is_file():
        raise SystemExit("Choose an installed Cygwin bash.exe using BRIDGE81_TEST_CYGWIN on Windows.")
    with tempfile.TemporaryDirectory(prefix="Bridge81 Cygwin spaces ") as directory:
        root = Path(directory).resolve()
        script = root / "a's $script.sh"
        with script.open("w", encoding="utf-8", newline="\n") as stream:
            stream.write("set -eu\nprintf '%s\\n' \"$1\" \"$2\" \"$3\"\nprintf 'z\\na\\n' | sort\n")
        with patch.dict(os.environ, {"PATH": str(Path(os.environ["SystemRoot"]) / "System32")}):
            result = run(bash_plan(script, ["two words", "$(touch INJECTED)", "é"], bash=bash), timeout=30)
        assert result.returncode == 0, result.output
        assert result.output.splitlines() == ["two words", "$(touch INJECTED)", "é", "a", "z"], result.output
        assert not (root / "INJECTED").exists()
        with script.open("w", encoding="utf-8", newline="\n") as stream:
            stream.write("/bin/sleep 30 &\nwait\n")
        result = run(bash_plan(script, bash=bash), timeout=0.5)
        assert result.reason == "timeout", result
        assert result.elapsed_seconds < 8, result
    print("Cygwin smoke passed: real Bash, Windows paths, Unicode, literal arguments, Unix PATH and process cleanup.")


if __name__ == "__main__":
    main()
