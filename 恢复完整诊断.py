"""Restore the byte-identical desktop diagnostic ZIP using Python's standard library."""
from pathlib import Path
import hashlib
import json
import os
import sys

ROOT = Path(__file__).resolve().parent

def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()

def verify_desktop():
    entries = json.loads((ROOT / 'SHA256SUMS.json').read_text(encoding='utf-8'))['files']
    for row in entries:
        path = ROOT / row['path']
        if not path.is_file() or path.stat().st_size != row['bytes'] or digest(path) != row['sha256']:
            raise RuntimeError('文件与桌面交付版不一致：' + row['path'])
    print('桌面交付清单全部通过：', len(entries), '个文件')

def main():
    spec = json.loads((ROOT / '诊断完整明细_分卷/manifest.json').read_text(encoding='utf-8'))
    output = ROOT / spec['output']
    if output.exists():
        if output.stat().st_size != spec['bytes'] or digest(output) != spec['sha256']:
            raise RuntimeError('已有同名ZIP与桌面版不同。请先自行保留或移动它，本程序不覆盖。')
    else:
        temporary = output.with_name(output.name + '.assembling')
        try:
            with temporary.open('xb') as target:
                for row in spec['parts']:
                    path = ROOT / row['path']
                    if path.stat().st_size != row['bytes'] or digest(path) != row['sha256']:
                        raise RuntimeError('分卷校验失败：' + row['path'])
                    with path.open('rb') as source:
                        for chunk in iter(lambda: source.read(1024 * 1024), b''):
                            target.write(chunk)
            if temporary.stat().st_size != spec['bytes'] or digest(temporary) != spec['sha256']:
                raise RuntimeError('恢复后的ZIP校验失败')
            os.replace(temporary, output)
        except Exception:
            # Keep an incomplete file for inspection; never overwrite an existing result.
            raise
    print('完整诊断ZIP已恢复，SHA256：', spec['sha256'])
    verify_desktop()

if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        print(str(error), file=sys.stderr)
        sys.exit(1)
