#!/bin/sh
# SAT Channel Manager Pro RC4.1 — hotfix for OpenATV 8.0.1 modal crash
set -eu
FILE="${SATCM_PLUGIN_PATH:-/usr/lib/enigma2/python/Plugins/Extensions/SATChannelManager/plugin.py}"
[ -f "$FILE" ] || { echo "ERROR: plugin.py not found: $FILE" >&2; exit 1; }
command -v python3 >/dev/null 2>&1 || { echo 'ERROR: python3 missing' >&2; exit 1; }
python3 - "$FILE" <<'PY'
import os
import shutil
import stat
import sys
import tempfile

path = sys.argv[1]
with open(path, 'rb') as handle:
    original = handle.read()
old = b'self.items'
new = b'self.choice_rows'
if old not in original:
    if new in original:
        print('SAT Channel Manager: modal hotfix already applied. Restart Enigma2 GUI if needed.')
        sys.exit(0)
    sys.exit('ERROR: incompatible plugin version (expected SATListView not found). No changes made.')
if b'class SATListView(Screen):' not in original or original.count(old) != 3:
    sys.exit('ERROR: unexpected RC4.1 layout. Refusing to modify plugin.py.')
patched = original.replace(old, new)
try:
    compile(patched, path, 'exec')
except Exception as exc:
    sys.exit('ERROR: patched Python source failed validation: %s' % exc)
backup = path + '.backup-before-modal-hotfix'
if not os.path.isfile(backup):
    shutil.copy2(path, backup)
st = os.stat(path)
fd, temporary = tempfile.mkstemp(prefix='.satcm-hotfix-', suffix='.py', dir=os.path.dirname(path))
try:
    with os.fdopen(fd, 'wb') as handle:
        handle.write(patched)
        handle.flush()
        os.fsync(handle.fileno())
    os.chmod(temporary, stat.S_IMODE(st.st_mode))
    os.replace(temporary, path)
finally:
    if os.path.exists(temporary):
        os.unlink(temporary)
print('SAT Channel Manager RC4.1: modal hotfix applied successfully.')
print('Backup: %s' % backup)
print('Restart the Enigma2 GUI before opening the plugin again.')
PY
