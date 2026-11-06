#!/usr/bin/env python3
"""Stage a subset of a file's diff hunks. See TOOL.md."""
import re
import subprocess
import sys


def hunks(path):
    diff = subprocess.run(['git', 'diff', '--no-color', '-U3', '--', path],
                          capture_output=True, text=True, check=True).stdout
    parts = re.split(r'(?m)^(?=@@ )', diff)
    return parts[0], parts[1:]


def main(argv):
    if len(argv) < 2 or argv[0] not in ('list', 'stage', 'show'):
        sys.exit('usage: git-hunks list <file> | stage <file> <i,j,...> | show <file> <i,j,...>')
    cmd, path = argv[0], argv[1]
    head, hs = hunks(path)
    if not hs:
        sys.exit(f'no unstaged change in {path}')
    if cmd == 'list':
        for i, h in enumerate(hs):
            lines = h.splitlines()
            changed = [l for l in lines[1:] if l[:1] in '+-'][:2]
            print(f'{i}  {lines[0][:100]}')
            for l in changed:
                print(f'     {l[:100]}')
        return
    if len(argv) < 3:
        sys.exit('missing hunk indexes, e.g. 0,2')
    keep = {int(x) for x in argv[2].split(',')}
    bad = keep - set(range(len(hs)))
    if bad:
        sys.exit(f'unknown hunk(s) {sorted(bad)}: {path} has {len(hs)} (0-{len(hs) - 1})')
    patch = head + ''.join(h for i, h in enumerate(hs) if i in keep)
    if cmd == 'show':
        sys.stdout.write(patch)
        return
    subprocess.run(['git', 'apply', '--cached'], input=patch, text=True, check=True)
    print(f'staged {len(keep)}/{len(hs)} hunk(s) of {path}')


if __name__ == '__main__':
    main(sys.argv[1:])
