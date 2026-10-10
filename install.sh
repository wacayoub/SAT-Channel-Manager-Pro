#!/bin/sh
# SAT Channel Manager Pro — audited RC4.1 + Easy Mode menu patch.
# The package and patch are checked before any installation is attempted.
set -eu
BASE='https://raw.githubusercontent.com/wacayoub/SAT-Channel-Manager-Pro/main'
PACKAGE='enigma2-plugin-extensions-satchannelmanager_0.4.1-rc4.1_all.ipk'
PACKAGE_SHA256='4eed0b5c1c61cf2e763b431a57ef5b2977d845164a345bef439991242595762a'
EASY_NAME='easy-mode-rc4.1.py'
EASY_GIT_BLOB_SHA1='43599a4ebae595c2b364b029ff2ee18860c9746e'
DEST="/tmp/$PACKAGE"
PATCH="/tmp/$EASY_NAME"
for dep in opkg wget sha256sum python3; do
    command -v "$dep" >/dev/null 2>&1 || { echo "ERROR: missing $dep" >&2; exit 1; }
done
trap 'rm -f "$DEST.part" "$PATCH.part"' EXIT HUP INT TERM
echo 'Downloading SAT Channel Manager Pro...'
wget -q -T 30 -t 2 -O "$DEST.part" "$BASE/packages/$PACKAGE" || { echo 'ERROR: IPK download failed' >&2; exit 1; }
ACTUAL_SHA="$(sha256sum "$DEST.part" | awk '{print $1}')"
[ "$ACTUAL_SHA" = "$PACKAGE_SHA256" ] || { echo 'ERROR: IPK checksum mismatch' >&2; exit 1; }
echo 'Downloading Easy Mode update...'
wget -q -T 30 -t 2 -O "$PATCH.part" "$BASE/$EASY_NAME" || { echo 'ERROR: Easy Mode download failed' >&2; exit 1; }
python3 - "$PATCH.part" "$EASY_GIT_BLOB_SHA1" <<'PY'
import hashlib, sys
data = open(sys.argv[1], 'rb').read()
git_sha = hashlib.sha1(('blob %d\0' % len(data)).encode() + data).hexdigest()
if git_sha != sys.argv[2]:
    raise SystemExit('ERROR: Easy Mode integrity check failed. No installation attempted.')
print('Easy Mode checksum verified.')
PY
mv -f "$DEST.part" "$DEST"
mv -f "$PATCH.part" "$PATCH"
echo 'Installing validated IPK...'
opkg install "$DEST" || { echo 'ERROR: opkg install failed; no Easy Mode patch applied.' >&2; exit 1; }
echo 'Applying Easy Mode patch...'
python3 "$PATCH"
echo 'Complete. Restart Enigma2 GUI via OpenATV menu.'
echo 'No satellite scan or bouquet modification was performed by this installer.'
