#!/bin/sh
# Hugging Face Spaces entrypoint — har start pe GitHub se fresh code pull karta hai.
set -e
python3 - << 'PYEOF'
import zipfile, shutil, os, urllib.request
urllib.request.urlretrieve(
    'https://github.com/pclwaqas786-ctrl/schoolweb/archive/refs/heads/master.zip',
    '/tmp/sw.zip')
skip = ('build_demo.py', 'render.yaml', 'Dockerfile', 'hf-entrypoint.sh',
        '.gitignore', 'requirements.txt')
z = zipfile.ZipFile('/tmp/sw.zip')
for m in z.namelist():
    rel = m.split('/', 1)[1] if '/' in m else m
    if not rel or rel.split('/')[-1] in skip:
        continue
    z.extract(m, '/tmp/sw')
src = '/tmp/sw/schoolweb-master'
for item in os.listdir(src):
    s = os.path.join(src, item)
    d = os.path.join('/app', item)
    if os.path.isdir(s):
        shutil.copytree(s, d, dirs_exist_ok=True)
    else:
        shutil.copy2(s, d)
PYEOF
rm -rf /tmp/sw.zip /tmp/sw
exec gunicorn app:app --bind 0.0.0.0:${PORT:-7860} --workers 2
