# Very quick and dirty driver for gnuplot

import os
import re
from pyPgSQL import PgSQL

def clean(x):
    return re.sub('[^-a-zA-Z0-9]', '_', x)

n = 0
files = {}
db = PgSQL.connect(database='httpinteract')
curs = db.cursor()
try:
    curs.execute('SELECT started, siteinfo, elapsed FROM reports')
    for row in curs.fetchall():
        siteinfo = clean(row.siteinfo)
        try:
            f = files[siteinfo]
        except KeyError:
            f = files[siteinfo] = open('siteinfo_' + siteinfo, 'w')
            n += 1
        f.write('%s %s\n' % (row.started, row.elapsed))
finally:
    curs.close()
# Must explicitly close DB, or no exclusive locks can occur.
db.close()
lines = []
for n, f in files.items():
    f.close()
    lines.append('"siteinfo_%s" using 1:3' % n)
cmds = r"""\
set timefmt "%Y-%m-%d %H:%M:%S"
set logscale y
set xdata time
plot """ + ', '.join(lines)

f = os.popen('gnuplot -', 'w')
print >> f, cmds
f.flush()
raw_input()

for n in files.keys():
    os.unlink('siteinfo_' + n)
