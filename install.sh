#!/bin/sh
# SAT Channel Manager Pro — install verified RC4.1 plus modal crash hotfix
set -eu
BASE='https://raw.githubusercontent.com/wacayoub/SAT-Channel-Manager-Pro/main'
PACKAGE='enigma2-plugin-extensions-satchannelmanager_0.4.1-rc4.1_all.ipk'
EXPECTED_SHA256='4eed0b5c1c61cf2e763b431a57ef5b2977d845164a345bef439991242595762a'
HOTFIX='hotfix-rc4.1.sh'
HOTFIX_SHA256='bc8ff27fd8e82435491d1e4cf1fbb31efb8130f468d0331977eeb018261d7ae5'
DEST="/tmp/$PACKAGE"
PATCH="/tmp/satcm-$HOTFIX"
for dep in opkg sha256sum wget python3; do
    command -v "$dep" >/dev/null 2>&1 || { echo "ERROR: $dep missing" >&2; exit 1; }
done
trap 'rm -f "$DEST.part" "$PATCH.part"' EXIT HUP INT TERM
check_hash() {
    got="$(sha256sum "$1" | awk '{print $1}')"
    [ "$got" = "$2" ] || { echo "ERROR: SHA256 mismatch for $1" >&2; exit 1; }
}
echo 'Downloading SAT Channel Manager Pro RC4.1...'
wget -q -T 30 -t 2 -O "$DEST.part" "$BASE/packages/$PACKAGE"
check_hash "$DEST.part" "$EXPECTED_SHA256"
echo 'Downloading OpenATV 8.0.1 modal crash hotfix...'
wget -q -T 30 -t 2 -O "$PATCH.part" "$BASE/$HOTFIX"
check_hash "$PATCH.part" "$HOTFIX_SHA256"
mv -f "$DEST.part" "$DEST"
mv -f "$PATCH.part" "$PATCH"
echo 'SHA256 verified. Installing package...'
opkg install "$DEST"
echo 'Applying verified modal hotfix...'
sh "$PATCH"
echo 'Installed and hotfixed. Restart the Enigma2 GUI through OpenATV menu.'
echo 'No scan or bouquet modification was performed.'
