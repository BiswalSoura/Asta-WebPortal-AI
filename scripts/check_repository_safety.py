"""Check versionable files, never .env values. Fail with paths only, never matched content."""

import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
KEY_PATTERN = re.compile(r'\b(?:gsk_|hf_|sk-)[A-Za-z0-9_-]{20,}')
PRIVATE_KEY = re.compile(r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----')


def unsafe_content(text):
    return bool(KEY_PATTERN.search(text) or PRIVATE_KEY.search(text))


def main():
    paths = subprocess.check_output(
        ['git', 'ls-files', '--cached', '--others', '--exclude-standard', '-z'], cwd=ROOT,
    ).decode().split('\0')
    failures = []
    for name in set(filter(None, paths)):
        path = Path(name)
        if ((path.name == '.env' or path.name.startswith('.env.')) and path.name != '.env.example'
                or name.startswith('data/evaluation/results/')):
            failures.append(name)
            continue
        absolute = ROOT / path
        if absolute.is_file() and unsafe_content(absolute.read_text(encoding='utf-8', errors='replace')):
            failures.append(name)
    for name in ['.env', '.env.local', '.cache/probe', 'logs/probe.log',
                 'data/evaluation/results/probe.json', '.venv/probe']:
        if subprocess.run(['git', 'check-ignore', '-q', '--no-index', name], cwd=ROOT).returncode:
            failures.append('ignore:' + name)
    for line in (ROOT / '.env.example').read_text().splitlines():
        if '=' in line and not line.lstrip().startswith('#'):
            key, value = line.split('=', 1)
            if key.upper().endswith(('_KEY', '_TOKEN', '_SECRET', '_PASSWORD', 'DATABASE_URL')) and value.strip():
                failures.append('.env.example')
    if failures:
        print('FAIL: repository safety: ' + ', '.join(sorted(set(failures))))
        return 1
    print('PASS: environment exclusions, example placeholders and credential signatures')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
