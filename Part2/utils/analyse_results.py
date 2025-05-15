#!/usr/bin/env python3
from pathlib import Path
import re, statistics, matplotlib.pyplot as plt, texttable as tt, json

files = {
    'linear':  'outputs/linear.txt',
    'minimal': 'outputs/minimal.txt',
    'tree':    'outputs/tree.txt',
    'torus':   'outputs/torus.txt',
    'full':    'outputs/full.txt'
}

rx_rtt = re.compile(r'rtt[^=]*=\s*[^/]+/([\d\.]+)/', re.I)
rx_tp  = re.compile(r'([\d\.]+)\s*(G|M)bit[s]?/sec', re.I)

def classify(line):
    l = line.lower()
    if 'udp' in l or '%)' in l or 'jitter' in l:
        return 'udp'
    return 'tcp'

def mean_std(xs):
    return (statistics.mean(xs) if xs else 0.0,
            statistics.stdev(xs) if len(xs) > 1 else 0.0)

results = {}
for topo, path in files.items():
    rtt, tcp, udp = [], [], []
    for line in Path(path).read_text().splitlines():
        m = rx_rtt.search(line)
        if m:
            rtt.append(float(m.group(1)))
        m = rx_tp.search(line)
        if m:
            v = float(m.group(1)) * (1000 if m.group(2).upper() == 'G' else 1)
            (udp if classify(line) == 'udp' else tcp).append(v)
    results[topo] = {'rtt': rtt, 'tcp': tcp, 'udp': udp}

tab = tt.Texttable(); tab.set_cols_align(['l','r','r','r','r','r','r'])
tab.add_row(['Topo','RTT µ','RTT σ','TCP µ','TCP σ','UDP µ','UDP σ'])
for t,d in results.items():
    rmu,rsig = mean_std(d['rtt'])
    cmu,csig = mean_std(d['tcp'])
    umu,usig = mean_std(d['udp'])
    tab.add_row([t,'%.2f'%rmu,'%.2f'%rsig,'%.1f'%cmu,'%.1f'%csig,'%.1f'%umu,'%.1f'%usig])
print(tab.draw())

out = Path('outputs'); out.mkdir(exist_ok=True)
labels = list(files.keys())
for m,y in [('rtt','RTT (ms)'),('tcp','TCP (Mb/s)'),('udp','UDP (Mb/s)')]:
    means = [statistics.mean(results[t][m]) if results[t][m] else 0 for t in labels]
    plt.figure(); plt.bar(labels, means); plt.ylabel(y); plt.title('Mean '+y)
    plt.savefig(str(out/('{}_bar.png'.format(m))), bbox_inches='tight')
for m,title in [('tcp','TCP'),('udp','UDP')]:
    data = [results[k][m] for k in labels]
    plt.figure(); plt.boxplot(data, labels=[k.capitalize() for k in labels])
    plt.ylabel('Mb/s'); plt.title(title+' Box‑Plot')
    plt.savefig(str(out/('{}_box.png'.format(m))), bbox_inches='tight')
(out/'summary.json').write_text(json.dumps(results, indent=2))
print('\nCharts and summary saved in outputs/')

