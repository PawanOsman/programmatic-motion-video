#!/usr/bin/env python3
"""Find icons by word and see them.

    python tools/find_icons.py money                 names matching 'money' (by name and tags)
    python tools/find_icons.py arrow --sheet a.png   also render a contact sheet of the matches
    python tools/find_icons.py --all --sheet all.png every icon (1,854) on one sheet

Draw one with icons.draw(c, 'rocket', x, y, 48, '#FFFFFF').
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'engine'))
import icons  # noqa: E402


def main():
    args = sys.argv[1:]
    if not args:
        sys.exit(__doc__)
    sheet = args[args.index('--sheet') + 1] if '--sheet' in args else None
    if '--all' in args:
        found = icons.names()
    else:
        words = [a for a in args if not a.startswith('--') and a != sheet]
        found = []
        for w in words:
            found += [n for n in icons.search(w, 200) if n not in found]
    print(f'{len(found)} icons')
    print(' '.join(found))
    if sheet:
        print(icons.sheet(found, sheet, cols=14 if len(found) > 100 else 10, size=56 if len(found) > 100 else 72))


if __name__ == '__main__':
    main()
