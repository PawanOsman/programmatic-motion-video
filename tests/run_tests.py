#!/usr/bin/env python3
"""Run the tests without pytest.

    python tests/run_tests.py                  engine tests (about a minute)
    python tests/run_tests.py --templates      also every template: info, a contact sheet, a small render
    python tests/run_tests.py -k sfx           only tests whose name contains "sfx"
    python tests/run_tests.py --templates -k promo

Exit code 0 when everything passed (skips for missing optional packages are fine).
"""
import argparse
import os
import sys
import time
import traceback

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)


def collect(module):
    return [(name, getattr(module, name)) for name in module.__dict__
            if name.startswith('test_') and callable(getattr(module, name))]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--templates', action='store_true', help='also run every template (several minutes)')
    ap.add_argument('--only-templates', action='store_true', help='run only the template checks')
    ap.add_argument('-k', default='', help='run tests whose name contains this text')
    ap.add_argument('-x', action='store_true', help='stop at the first failure')
    a = ap.parse_args()

    tests = []
    if not a.only_templates:
        import test_engine
        tests += collect(test_engine)
    if a.templates or a.only_templates:
        import test_templates
        tests += test_templates.cases()
    tests = [(n, f) for n, f in tests if a.k in n]

    passed, failed, skipped = 0, [], []
    t_all = time.time()
    for name, fn in tests:
        t0 = time.time()
        print(f'{name:<48}', end=' ', flush=True)
        try:
            fn()
        except (KeyboardInterrupt, SystemExit):
            raise
        except BaseException as e:                     # pytest.skip raises a BaseException
            if type(e).__name__ in ('Skip', 'Skipped'):
                skipped.append(name)
                print(f'skip  ({e})')
                continue
            failed.append(name)
            print(f'FAIL  {time.time() - t0:5.1f}s')
            traceback.print_exc()
            if a.x:
                break
            continue
        passed += 1
        print(f'ok    {time.time() - t0:5.1f}s')
    print(f'\n{passed} passed, {len(failed)} failed, {len(skipped)} skipped in {time.time() - t_all:.0f}s')
    if failed:
        print('failed: ' + ', '.join(failed))
    sys.exit(1 if failed else 0)


if __name__ == '__main__':
    main()
