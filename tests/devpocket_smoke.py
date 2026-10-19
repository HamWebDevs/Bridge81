"""Explicit installed-wheel API v1 integration; no game code is executed."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile

from helpers import game
from import_helpers import import_pe


def command(args, root, *, expected=0, input=None):
    result = subprocess.run([sys.executable, '-m', 'devpocket', *map(str, args)], cwd=root,
                            text=True, input=input, capture_output=True, timeout=30)
    assert result.returncode == expected, result.stdout + '\n' + result.stderr
    return result.stdout


def main():
    with tempfile.TemporaryDirectory(prefix='bridge81-integration-') as directory:
        root = Path(directory).resolve()
        story = game(root / 'Story')
        import_pe(story / 'Story.exe', imports=('KERNEL32.dll', 'api-ms-win-crt-heap-l1-1-0.dll'))
        inventory = json.loads(command(['plugins', 'list', '--json'], root))
        assert any(p['name'] == 'bridge81-game' and not p['enabled'] for p in inventory)
        payload = json.dumps({'folder': 'Story'})
        command(['run', 'bridge81-game', '--input', payload], root, expected=2)
        command(['plugins', 'enable', 'bridge81-game'], root)
        report = json.loads(command(['run', 'bridge81-game', '--input', payload, '--format', 'json'], root))
        assert report['data']['game']['status'] == 'unverified'
        assert report['data']['dependencies']['summary']['imports'] == 2
        assert str(root) not in json.dumps(report)
        assert 'MUST NOT EXECUTE' not in json.dumps(report)
        assert all(i['availability'] == 'not-in-inspected-bundle-folders'
                   for i in report['data']['dependencies']['modules'][0]['imports'])

        # Actual bundle evidence is a warning, not proof of Windows resolution.
        import_pe(story / 'Story.exe', imports=('vcruntime140.dll',))
        import_pe(story / 'vcruntime140.dll', bits=32)
        sarif = json.loads(command(['run', 'bridge81-game', '--input', payload, '--format', 'sarif'], root, expected=1))
        assert any(r['ruleId'].endswith('bundled-dll-different-architecture') for r in sarif['runs'][0]['results'])
        assert all(not r.get('locations') or r['locations'][0]['physicalLocation']['artifactLocation']['uri'].startswith('Story/')
                   for r in sarif['runs'][0]['results'])
        (story / 'vcruntime140.dll').unlink()

        messages = [{'jsonrpc': '2.0', 'id': 1, 'method': 'initialize', 'params': {
            'protocolVersion': '2025-11-25', 'capabilities': {}, 'clientInfo': {'name': 'bridge81-test', 'version': '1'}}},
            {'jsonrpc': '2.0', 'method': 'notifications/initialized'},
            {'jsonrpc': '2.0', 'id': 2, 'method': 'tools/list'},
            {'jsonrpc': '2.0', 'id': 3, 'method': 'tools/call', 'params': {'name': 'bridge81-game', 'arguments': {'folder': 'Story'}}}]
        replies = {x['id']: x for x in map(json.loads, command(['serve', '--root', root, '--plugin', 'bridge81-game'], root,
                    input=''.join(json.dumps(m) + '\n' for m in messages)).splitlines())}
        advertised = next(t for t in replies[2]['result']['tools'] if t['name'] == 'bridge81-game')
        assert advertised['annotations']['readOnlyHint'] is True
        assert not replies[3]['result']['isError']
        assert replies[3]['result']['structuredContent']['data']['dependencies']['summary']['imports'] == 1

        # A known OS blocker is an operational outcome, even with suppression.
        (story / 'renpy/__init__.py').write_text("version_tuple = (8, 4, 0)\nraise RuntimeError('MUST NOT EXECUTE')\n")
        blocked = command(['run', 'bridge81-game', '--input', payload, '--format', 'json', '--fail-on', 'none'], root, expected=1)
        (root / 'blocked.json').write_text(blocked)
        command(['baseline', '--from', 'blocked.json', '--output', 'baseline.json'], root)
        command(['run', 'bridge81-game', '--input', payload, '--baseline', 'baseline.json', '--fail-on', 'none'], root, expected=1)
        print('Installed DevPocket discovery, read-only DLL evidence, SARIF, MCP and unsuppressible OS blocker checks passed.')


if __name__ == '__main__':
    main()
