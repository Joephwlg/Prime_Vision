"""Throwaway: exec a range of code cells from a notebook in-process."""
import json, os, sys, traceback
import matplotlib; matplotlib.use('Agg')

if len(sys.argv) < 2:
    print('usage: _run_cells.py <notebook.ipynb> [start] [end]'); sys.exit(2)
NB = sys.argv[1]
start = int(sys.argv[2]) if len(sys.argv) > 2 else 0
end   = int(sys.argv[3]) if len(sys.argv) > 3 else 999

cells = json.load(open(NB, encoding='utf-8'))['cells']
g = {'__name__': '__main__'}
for i, c in enumerate(cells):
    if i < start or i > end or c['cell_type'] != 'code':
        continue
    src = ''.join(c['source'])
    print(f'\n=== cell {i} ===')
    try:
        exec(compile(src, f'<cell {i}>', 'exec'), g)
    except Exception:
        traceback.print_exc(); sys.exit(1)
print('\nOK')
