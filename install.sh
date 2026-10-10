#!/bin/sh
# SAT Channel Manager Pro — install from verified GitHub package.
set -eu
BASE='https://raw.githubusercontent.com/wacayoub/SAT-Channel-Manager-Pro/main'
PACKAGE='enigma2-plugin-extensions-satchannelmanager_0.4.1-rc4.1_all.ipk'
EXPECTED_SHA256='4eed0b5c1c61cf2e763b431a57ef5b2977d845164a345bef439991242595762a'
DEST="/tmp/$PACKAGE"
if ! command -v opkg >/dev/null 2>&1; then
  echo 'ERROR: opkg missing. Requires an Enigma2 receiver with opkg.' >&2; exit 1
fi
if ! command -v sha256sum >/dev/null 2>&1; then
  echo 'ERROR: sha256sum missing; cannot validate package.' >&2; exit 1
fi
if ! command -v wget >/dev/null 2>&1; then
  echo 'ERROR: wget missing.' >&2; exit 1
fi
trap 'rm -f "$DEST.part"' EXIT HUP INT TERM
echo 'Downloading SAT Channel Manager Pro RC4.1...'
wget -q -T 30 -t 2 -O "$DEST.part" "$BASE/packages/$PACKAGE" || {
  echo 'ERROR: download failed or package not yet published; no installation attempted.' >&2
  exit 1
}
ACTUAL_SHA256="$(sha256sum "$DEST.part" | awk '{print $1}')"
if [ "$ACTUAL_SHA256" != "$EXPECTED_SHA256" ]; then
  echo 'ERROR: SHA256 mismatch; refusing installation.' >&2
  exit 1
fi
mv -f "$DEST.part" "$DEST"
echo 'SHA256 verified. Installing package...'
opkg install "$DEST"
echo 'Installed. Restart the Enigma2 GUI through OpenATV to load the plugin.'
echo 'No channel scans or bouquet changes were performed by this installer.'
