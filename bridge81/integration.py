"""Optional DevPocket API v1 adapter. No host dependency during standalone use."""


def inspect(context, params):
    import json
    from devpocket.sdk import Finding, ToolResult
    from .dependencies import inspect_dependencies
    from .renpy import inspect_game

    folder = context.resolve(params['folder'])
    options = {key: params[key] for key in ('exe', 'target') if key in params}
    game = inspect_game(folder, **options)
    prefix = folder.relative_to(context.root)
    findings = [Finding(item.code, item.message, severity={'blocked': 'error', 'warning': 'warning', 'info': 'note'}[item.level], path=(prefix / game.executable).as_posix() if game.executable else None, help=item.action or None) for item in game.findings]
    data = {'game': game.as_dict()}
    incomplete = False
    if params.get('dependencies', True) and game.executable:
        evidence = inspect_dependencies(folder, **options)
        data['dependencies'] = evidence
        incomplete = bool(evidence['summary']['unreadable_modules'])
        findings += [Finding(item['code'], item['message'], path=(prefix / item['path']).as_posix()) for item in evidence['findings']]
    # Tuples in the standalone dataclass become arrays at the SDK JSON boundary.
    data = json.loads(json.dumps(data, allow_nan=False))
    return ToolResult('Bridge81 read-only game evidence: ' + game.status, findings, data, exit_code=1 if game.status == 'blocked' or incomplete else 0)


def build_tool():
    from devpocket.sdk import ToolSpec
    return ToolSpec(name='bridge81-game', description='Inspect RenPy engine metadata, PE headers and DLL imports without executing or repairing the game', input_schema={'type': 'object', 'properties': {'folder': {'type': 'string', 'minLength': 1, 'maxLength': 4096}, 'exe': {'type': 'string', 'maxLength': 1024}, 'target': {'type': 'string', 'enum': ['x86', 'x64']}, 'dependencies': {'type': 'boolean'}}, 'required': ['folder'], 'additionalProperties': False}, run=inspect, read_only=True, api_version=1)


def inspect_runtime_log(context, params):
    from devpocket.sdk import Finding, ToolResult
    from .runtime_log import load
    requested = context.root / params['log']
    if requested.is_symlink():
        raise ValueError('Runtime log cannot be a symlink')
    path = context.resolve(params['log'])
    # Check the lexical path too, before resolve can erase an internal link.
    for parent in requested.parents:
        if parent == context.root:
            break
        if parent.is_symlink():
            raise ValueError('Runtime log cannot use symlinked directories')
    report = load(path)
    relative = path.relative_to(context.root).as_posix()
    findings = [Finding(item['code'], item['message'], path=relative, line=item['first_line'], help=item['action']) for item in report['findings']]
    return ToolResult('Saved runtime-log hints: ' + report['status'], findings, report)


def build_runtime_log_tool():
    from devpocket.sdk import ToolSpec
    return ToolSpec(name='bridge81-runtime-log', description='Classify saved Windows loader, import and graphics error hints while withholding log lines and private paths', input_schema={'type': 'object', 'properties': {'log': {'type': 'string', 'minLength': 1, 'maxLength': 4096}}, 'required': ['log'], 'additionalProperties': False}, run=inspect_runtime_log, read_only=True, api_version=1)
