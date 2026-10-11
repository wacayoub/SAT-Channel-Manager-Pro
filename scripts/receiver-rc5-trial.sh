#!/bin/sh
# SAT Channel Manager Pro RC5 Trial — Vu+ Zero 4K / OpenATV 8.0.1
# --build-only: download/validate/build in /tmp, no receiver file touched
# --install:    above + backup and opkg install (never scan or change bouquets)
set -eu
MODE="--build-only"
[ "$#" -eq 0 ] || MODE="$1"
case "$MODE" in
  --build-only|--install) ;;
  *) echo "Usage: sh receiver-rc5-trial.sh [--build-only|--install]" >&2; exit 2 ;;
esac

# CI may pin a commit SHA to avoid stale raw.githubusercontent.com branch cache.
BASE="${SATCM_SOURCE_BASE:-https://raw.githubusercontent.com/wacayoub/SAT-Channel-Manager-Pro/feature/rc5-trial-validation}"
WORK="/tmp/satcm-rc5-source"
OUT="/tmp/satcm-rc5-trial.ipk"
SRC="$WORK/packages/enigma2-plugin-extensions-satchannelmanager_0.4.1-rc4.1_all.ipk"
HASH="4eed0b5c1c61cf2e763b431a57ef5b2977d845164a345bef439991242595762a"
PKG="enigma2-plugin-extensions-satchannelmanager"
BACKUP_DIR="/home/root/satcm-backups"
PLUGIN="usr/lib/enigma2/python/Plugins/Extensions/SATChannelManager"

for dep in python3 wget sha256sum tar sed grep cp date mkdir; do
  command -v "$dep" >/dev/null 2>&1 || {
    echo "ERROR: required command missing: $dep; no installation." >&2
    exit 1
  }
done
mkdir -p "$WORK/scripts" "$WORK/packages"
for item in \
  "scripts/build-rc5-trial.py" \
  "easy-mode-rc4.1.py" \
  "neo-icons-easy-rc4.1.py" \
  "scripts/service_sources_rc5.py" \
  "scripts/service_sources_rc5_ui.py" \
  "packages/enigma2-plugin-extensions-satchannelmanager_0.4.1-rc4.1_all.ipk"
do
  echo "Download $item ..."
  wget -q -T 30 -t 2 -O "$WORK/$item.part" "$BASE/$item" || {
    echo "ERROR: download failed, receiver unchanged: $item" >&2; exit 1;
  }
  [ -s "$WORK/$item.part" ] || {
    echo "ERROR: downloaded an empty file: $item" >&2; exit 1;
  }
  mv "$WORK/$item.part" "$WORK/$item"
done

ACTUAL="$(sha256sum "$SRC" | sed 's/[[:space:]].*$//')"
[ "$ACTUAL" = "$HASH" ] || {
  echo "ERROR: upstream RC4.1 IPK checksum mismatch; nothing installed." >&2
  exit 1
}

# Reject stale or mixed Github CDN source before creating an IPK.
grep -Fq 'VERSION = "0.5.1-rc5.1-trial"' "$WORK/scripts/build-rc5-trial.py" || {
  echo "ERROR: stale RC5.0 builder from GitHub cache; no installation." >&2
  exit 1
}
(cd "$WORK" && python3 scripts/build-rc5-trial.py)
[ -s "$WORK/rc5-trial.ipk" ] || { echo 'ERROR: no trial IPK' >&2; exit 1; }
cp "$WORK/rc5-trial.ipk" "$OUT"
echo "BUILD OK: $OUT"
sha256sum "$OUT"
if [ "$MODE" = "--build-only" ]; then
  echo "NO INSTALL: trial package built without changing the receiver."
  exit 0
fi

command -v opkg >/dev/null 2>&1 || {
  echo 'ERROR: opkg unavailable, installation refused.' >&2; exit 1;
}
[ -f "/$PLUGIN/plugin.py" ] || {
  echo 'ERROR: current SAT Channel Manager plugin missing; refuse update.' >&2; exit 1;
}
PKG_STATUS="$(opkg status "$PKG" 2>/dev/null || true)"
CURRENT="$(printf '%s\n' "$PKG_STATUS" | sed -n 's/^Version: //p' | sed -n '1p')"
case "$CURRENT" in
  0.4.1-rc4.1) ;;
  0.5.0-rc5-trial) ;;
  0.5.1-rc5.1-trial)
    echo "RC5 Trial already installed; nothing else changed."
    echo "Backup remains under $BACKUP_DIR."
    exit 0 ;;
  *) echo "ERROR: unsupported installed version '$CURRENT'. No changes." >&2; exit 1 ;;
esac

[ -d /home/root ] || {
  echo "ERROR: missing /home/root backup destination. No installation." >&2; exit 1;
}
mkdir -p "$BACKUP_DIR"
STAMP="$(date +%Y%m%d-%H%M%S)"
ARCHIVE="$BACKUP_DIR/before-rc5-$STAMP.tar.gz"
# Always include original plugin and only existing satellite/bouquet settings.
set -- "$PLUGIN"
for candidate in \
  /etc/enigma2/lamedb /etc/enigma2/lamedb5 \
  /etc/enigma2/bouquets.tv /etc/enigma2/bouquets.radio \
  /etc/enigma2/settings /etc/enigma2/userbouquet.* \
  /etc/tuxbox/satellites.xml
do
  if [ -f "$candidate" ]; then
    REL="$(printf '%s\n' "$candidate" | sed 's@^/@@')"
    set -- "$@" "$REL"
  fi
done
tar -czf "$ARCHIVE" -C / "$@"
tar -tzf "$ARCHIVE" >/dev/null
[ -s "$ARCHIVE" ] || {
  echo "ERROR: backup empty; install refused." >&2; exit 1;
}
cp "$SRC" "$BACKUP_DIR/rc4.1-restore.ipk"
printf '%s\n' "$ARCHIVE" > "$BACKUP_DIR/rc5-last-backup-path"
echo "BACKUP VERIFIED: $ARCHIVE"
# Write a separate, offline-capable recovery command BEFORE installation.
cat > "$BACKUP_DIR/rollback-rc5.sh" <<'RECOVER'
#!/bin/sh
set -eu
B="/home/root/satcm-backups"
A="$(cat "$B/rc5-last-backup-path")"
[ -s "$A" ] && [ -s "$B/rc4.1-restore.ipk" ] || {
  echo "ERROR: baseline or backup missing. Aborting rollback." >&2; exit 1;
}
tar -tzf "$A" >/dev/null
echo "Restoring SAT Channel Manager RC4.1 package ..."
opkg install --force-downgrade --force-reinstall "$B/rc4.1-restore.ipk"
echo "Restoring exact pre-RC5 plugin + settings files ..."
tar -xzf "$A" -C /
echo "Rollback completed. Restart Enigma2 GUI from OpenATV menu."
RECOVER
chmod 700 "$BACKUP_DIR/rollback-rc5.sh"
echo "RECOVERY READY: sh $BACKUP_DIR/rollback-rc5.sh"
echo "Installing RC5 Trial package (no scan/merge)..."
if ! opkg install "$OUT"; then
  echo "ERROR: opkg install failed. Original backup and recovery command remain available." >&2
  exit 1
fi
echo "RC5 TRIAL INSTALLED. Restart Enigma2 GUI from OpenATV menu."
echo "To restore: sh $BACKUP_DIR/rollback-rc5.sh"
echo "No scan, transponder merge, tuner change, or bouquet change was performed."
