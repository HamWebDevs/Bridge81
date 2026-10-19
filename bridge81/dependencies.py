"""Read-only DLL evidence. Bundle presence does not simulate the Windows loader."""
from __future__ import annotations

import os
from pathlib import Path
import re

from .model import BridgeError
from .pe import inspect_pe
from .pe_imports import inspect_imports
from .renpy import inspect_game

MAX_MODULES = 32
MAX_IMPORTS_TOTAL = 512
PLATFORM = re.compile(r'^(?:py\d+(?:\.\d+)*-)?(?:windows[-_](?:x86_64|amd64|i686|x86)|win[-_](?:amd64|x86)|win32)$', re.I)
PYTHON_DLL = re.compile(r'^(?:(?:lib)?python\d{1,3}(?:\.\d+)?(?:_d)?|librenpython)\.dll$', re.I)
SYSTEM = {'kernel32.dll', 'kernelbase.dll', 'ntdll.dll', 'user32.dll', 'gdi32.dll', 'advapi32.dll', 'shell32.dll', 'ole32.dll', 'oleaut32.dll', 'comdlg32.dll', 'comctl32.dll', 'ws2_32.dll', 'winmm.dll', 'version.dll', 'imm32.dll', 'setupapi.dll', 'msvcrt.dll', 'bcrypt.dll', 'crypt32.dll', 'rpcrt4.dll', 'shlwapi.dll', 'opengl32.dll', 'd3d9.dll', 'd3d11.dll', 'dxgi.dll', 'winhttp.dll', 'secur32.dll', 'normaliz.dll'}


def _safe(root, path):
    path = Path(path)
    try:
        path.resolve().relative_to(root)
    except ValueError as exc:
        raise BridgeError('Dependency input leaves the selected game folder.') from exc
    current = path
    while current != root:
        stat = current.lstat()
        if current.is_symlink() or getattr(stat, 'st_file_attributes', 0) & 0x400:
            raise BridgeError('Dependency inspection refuses symbolic links and junctions.')
        current = current.parent
    return path


def _files(root, folder, maximum=1024):
    _safe(root, folder)
    result = {}
    with os.scandir(folder) as entries:
        for index, entry in enumerate(entries):
            if index >= maximum:
                raise BridgeError('Dependency folder exceeds its entry limit.')
            if entry.is_file(follow_symlinks=False):
                key = entry.name.casefold()
                if key in result:
                    raise BridgeError('Bundle contains ambiguous case-insensitive file names.')
                result[key] = Path(entry.path)
    return result


def category(name):
    name = name.lower()
    if name == 'ucrtbase.dll' or name.startswith('api-ms-win-crt-'):
        return 'universal-crt'
    if re.match(r'^(vcruntime|msvcp|msvcr|concrt)\d', name):
        return 'visual-c-runtime'
    if name.startswith(('api-ms-win-', 'ext-ms-win-')):
        return 'windows-api-contract'
    return 'windows-system' if name in SYSTEM else 'application'


def inspect_dependencies(folder, *, exe=None, target='x64'):
    base = inspect_game(folder, exe=exe, target=target)
    root = Path(folder).expanduser().resolve()
    if base.executable is None:
        raise BridgeError('Choose the main game executable before inspecting DLL imports.')
    selected = _safe(root, root / base.executable)
    files = {root: _files(root, root)}
    candidates = [selected]
    lib = root / 'lib'
    if lib.is_dir():
        _safe(root, lib)
        with os.scandir(lib) as entries:
            for index, entry in enumerate(entries):
                if index >= 128:
                    raise BridgeError('Too many engine folders for dependency inspection.')
                if not PLATFORM.fullmatch(entry.name) or not entry.is_dir(follow_symlinks=False):
                    continue
                directory = _safe(root, Path(entry.path))
                inventory = _files(root, directory)
                files[directory] = inventory
                engine_names = {selected.name.casefold(), 'python.exe', 'pythonw.exe', 'renpy.exe'}
                candidates.extend(path for name, path in sorted(inventory.items()) if name in engine_names or PYTHON_DLL.fullmatch(name))
    if selected.parent not in files:
        files[selected.parent] = _files(root, selected.parent)
    modules, findings, imports_total = [], [], 0
    for path in dict.fromkeys(candidates):
        relative = path.relative_to(root).as_posix()
        if len(modules) >= MAX_MODULES:
            raise BridgeError('Dependency inspection exceeds 32 engine modules; narrow the game build.')
        try:
            _safe(root, path)
            pe = inspect_pe(path)
            imported = inspect_imports(path)
        except (BridgeError, OSError) as exc:
            modules.append({'path': relative, 'state': 'unreadable', 'imports': []})
            findings.append({'code': 'dependency-unreadable', 'level': 'warning', 'path': relative, 'message': str(exc)})
            continue
        records = []
        for load, names in (('direct', imported['imports']), ('delay', imported['delay_imports'])):
            for name in names:
                imports_total += 1
                if imports_total > MAX_IMPORTS_TOTAL:
                    raise BridgeError('Dependency inspection exceeds 512 imported library references.')
                nearby = []
                for directory in dict.fromkeys((path.parent, root)):
                    found = files.get(directory, {}).get(name.casefold())
                    if found is None:
                        continue
                    status, architecture = 'unreadable', None
                    try:
                        _safe(root, found)
                        architecture = inspect_pe(found).architecture
                        status = 'matching-architecture' if architecture == pe.architecture else 'different-architecture'
                    except (OSError, BridgeError):
                        pass
                    location = found.relative_to(root).as_posix()
                    nearby.append({'path': location, 'architecture': architecture, 'state': status, 'beside_importer': directory == path.parent})
                    if directory == path.parent and status != 'matching-architecture':
                        findings.append({'code': 'bundled-dll-' + status, 'level': 'warning', 'path': location, 'message': name + ' beside ' + relative + ' has ' + status.replace('-', ' ') + '. Review the bundled runtime; Windows loader rules still apply.'})
                records.append({'name': name, 'load': load, 'category': category(name), 'bundle_candidates': nearby, 'availability': 'bundle-evidence' if nearby else 'not-in-inspected-bundle-folders'})
        modules.append({'path': relative, 'state': 'inspected', 'architecture': pe.architecture, 'imports': records, 'bytes_read': imported['bytes_read']})
    return {'schema_version': 1, 'game': root.name, 'target': base.target, 'modules': modules, 'summary': {'modules': len(modules), 'imports': imports_total, 'unreadable_modules': sum(m['state'] != 'inspected' for m in modules), 'bundled_candidates': sum(len(i['bundle_candidates']) for m in modules for i in m['imports'])}, 'findings': findings, 'interpretation': 'Static direct/delay-import evidence only. No game or DLL was executed or loaded. Bundle presence is not loader resolution; absent bundle files may be provided by Windows or an installed runtime. API-set contracts are not ordinary missing files. Dynamic imports, export versions, CPU/GPU requirements and transitive dependencies are not resolved. Absolute paths and log contents are omitted.'}


def report_markdown(report):
    def safe(value):
        return str(value).replace('`', "'").replace('<', '&lt;').replace('>', '&gt;').replace('\n', ' ').replace('\r', ' ')
    lines = ['# Bridge81 DLL evidence', '', 'Game: `' + safe(report['game']) + '`', '', report['interpretation'], '']
    for module in report['modules']:
        lines.append('## ' + safe(module['path']))
        lines.append('')
        if module['state'] != 'inspected':
            lines += ['Import metadata could not be inspected.', '']
            continue
        lines += ['Architecture: ' + module['architecture'], '', '| Library | Import | Category | Bundle evidence |', '| --- | --- | --- | --- |']
        for item in module['imports']:
            evidence = '; '.join(c['path'] + ': ' + c['state'] for c in item['bundle_candidates']) or 'Not in inspected folders; system availability unknown'
            lines.append('| ' + ' | '.join(safe(v).replace('|', '\\|') for v in (item['name'], item['load'], item['category'], evidence)) + ' |')
        lines.append('')
    for finding in report['findings']:
        lines.append('- **warning** ' + safe(finding['message']))
    return '\n'.join(lines) + '\n'
