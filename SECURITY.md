# Security and privacy

Bridge81 is a local utility, not a sandbox or malware scanner. A selected script, interpreter, Cygwin tool or game runs with your normal account permissions. Use trusted inputs for execution. Inspection reads ordinary files and does not import game code or load executables.

The app has no telemetry, network listener, login or automatic runtime/game download. Official documentation opens only when a user chooses a link. The optional Python setup downloads from Python.org only, validates a pinned checksum and Authenticode signature, and stops if verification fails.

Reports omit absolute paths and log text, but game folder and executable names remain visible. Review reports before sharing. CLI command previews intentionally contain the local paths needed to review a run.

For a security issue, use GitHub's private vulnerability reporting if enabled. Do not post exploit details or sensitive logs publicly before maintainers can assess them. This preview makes no support or security-maintenance promise for the Windows 8.1 operating system or third-party legacy runtimes.
