#!/bin/sh
# SAT Channel Manager Pro: verified RC4.1 + Easy Mode.
# Re-running on an already installed RC4.1 skips opkg installation.
set -eu
BASE='https://raw.githubusercontent.com/wacayoub/SAT-Channel-Manager-Pro/main'
PKG='enigma2-plugin-extensions-satchannelmanager'
VERSION='0.4.1-rc4.1'
PACKAGE="${PKG}_${VERSION}_all.ipk"
PACKAGE_SHA256='4eed0b5c1c61cf2e763b431a57ef5b2977d845164a345bef439991242595762a'
EASY_NAME='easy-mode-rc4.1.py'
EASY_GIT_BLOB_SHA1='43599a4ebae595c2b364b029ff2ee18860c9746e'
DEST="/tmp/$PACKAGE"
PATCH="/tmp/$EASY_NAME"

for dep in opkg wget sha256sum python3 awk grep sed; do
    command -v "$dep" >/dev/null 2>&1 || {
        echo "ERROR: missing $dep" >&2; exit 1
    }
done
trap 'rm -f "$DEST.part" "$PATCH.part"' EXIT HUP INT TERM

PKG_STATUS="$(opkg status "$PKG" 2>/dev/null || true)"
INSTALLED=0
if printf '%s\n' "$PKG_STATUS" | grep -q '^Status: .*installed'; then
    INSTALLED=1
fi
CURRENT="$(printf '%s\n' "$PKG_STATUS" | sed -n 's/^Version: //p' | head -n 1)"
if [ "$INSTALLED" -eq 1 ] && [ "$CURRENT" != "$VERSION" ]; then
    echo "ERROR: installed version '$CURRENT', expected '$VERSION'. No changes made." >&2
    exit 1
fi

# Fetch and authenticate the patch before touching local Python files.
echo 'Downloading Easy Mode update...'
wget -q -T 30 -t 2 -O "$PATCH.part" "$BASE/$EASY_NAME" || {
    echo 'ERROR: Easy Mode download failed' >&2; exit 1
}
python3 - "$PATCH.part" "$EASY_GIT_BLOB_SHA1" <<'PY'
import hashlib, sys
data = open(sys.argv[1], 'rb').read()
git_sha = hashlib.sha1(('blob %d\0' % len(data)).encode() + data).hexdigest()
if git_sha != sys.argv[2]:
    raise SystemExit('ERROR: Easy Mode checksum mismatch. No changes made.')
print('Easy Mode checksum verified.')
PY
mv -f "$PATCH.part" "$PATCH"

if [ "$INSTALLED" -eq 1 ]; then
    echo "SAT Channel Manager $VERSION already installed; skipping opkg."
else
    echo 'Downloading SAT Channel Manager Pro package...'
    wget -q -T 30 -t 2 -O "$DEST.part" "$BASE/packages/$PACKAGE" || {
        echo 'ERROR: IPK download failed' >&2; exit 1
    }
    ACTUAL="$(sha256sum "$DEST.part" | awk '{print $1}')"
    [ "$ACTUAL" = "$PACKAGE_SHA256" ] || {
        echo 'ERROR: IPK checksum mismatch. No changes made.' >&2; exit 1
    }
    mv -f "$DEST.part" "$DEST"
    echo 'Installing validated IPK...'
    opkg install "$DEST" || {
        echo 'ERROR: opkg installation failed; Easy Mode not applied.' >&2; exit 1
    }
fi

echo 'Applying Easy Mode patch...'
python3 "$PATCH" || {
    echo 'ERROR: Easy Mode patch refused this local code revision.' >&2
    exit 1
}
echo 'Downloading Neo icons + satellite selection clarity update...'
NEO_PATCH='/tmp/satcm-neo-icons-easy-rc4.1.py'
NEO_BLOB_SHA1='8979466d8197b6c27497d9eeb094e6f765847e64'
wget -q -T 30 -t 2 -O "$NEO_PATCH.part" "$BASE/neo-icons-easy-rc4.1.py" || {
    echo 'ERROR: Neo icon update download failed' >&2; exit 1
}
python3 - "$NEO_PATCH.part" "$NEO_BLOB_SHA1" <<'PY'
import hashlib,sys
data=open(sys.argv[1],'rb').read()
digest=hashlib.sha1(('blob %d\0'%len(data)).encode()+data).hexdigest()
if digest!=sys.argv[2]:
    sys.exit('ERROR: Neo icon update checksum mismatch')
print('Neo icon update verified.')
PY
mv -f "$NEO_PATCH.part" "$NEO_PATCH"
python3 "$NEO_PATCH" || {
    echo 'ERROR: Neo icons update refused; previous installation left intact.' >&2; exit 1
}
echo 'Success. Restart the Enigma2 GUI from the OpenATV menu.'
echo 'No scan, transponder merge or bouquet modification was performed.'
