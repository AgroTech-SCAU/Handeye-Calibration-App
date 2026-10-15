#!/usr/bin/env python3
"""Check the intentional release baseline, independently of remote main"""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def git_blob_sha(path):
    data = path.read_bytes()
    return hashlib.sha1(f'blob {len(data)}\0'.encode()+data).hexdigest()


def verify():
    manifest = json.loads((ROOT/'docs/core-manifest.json').read_text(encoding='utf-8'))
    bad = []
    for rel, expected in manifest['files'].items():
        path = ROOT/rel
        actual = git_blob_sha(path) if path.exists() else 'MISSING'
        if actual != expected:
            bad.append((rel, actual, expected))
    return manifest, bad


if __name__ == '__main__':
    manifest, bad = verify()
    if bad:
        print('CORE INTEGRITY: FAIL')
        for rel, actual, expected in bad:
            print(f'  {rel}: {actual} != {expected}')
        raise SystemExit(1)
    print(f"CORE INTEGRITY: PASS ({len(manifest['files'])} files match release manifest)")
