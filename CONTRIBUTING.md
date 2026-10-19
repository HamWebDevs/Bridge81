# Contributing

Practical, small improvements are welcome. Useful areas include reproducible Windows 8.1 test results, documented Cygwin tool workflows, clearer game failure reports and accessibility improvements.

Open an issue with the intended workflow, OS/architecture, runtime versions and a minimal reproduction. Please remove private paths, usernames and game dialogue from logs before posting. Do not attach copyrighted game builds, saves or personal files.

Run `python -m unittest discover -s tests -v` before proposing code. GUI changes also need `python tests/gui_smoke.py` with a desktop display and a visual check at 1366×768. Use the [device checklist](docs/testing.md) for Windows 8.1 claims. Preview releases should stay labelled as such until those checks have evidence.

Keep runtime dependencies at zero unless an issue establishes a strong reason. Keep setup actions explicit, use official download sources, retain checksum/signature verification and keep inspection separate from execution. Do not add registry tuning, unsigned DLL replacements, hidden downloads, engine swaps or compatibility claims based on version guesses.

Use HamWebDevs for project credits and repository metadata. The MIT license applies to Bridge81 code; upstream runtimes and games retain their own terms.
