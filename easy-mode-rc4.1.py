#!/usr/bin/env python3
# SAT Channel Manager Pro RC4.1 -> Easy Mode hotfix for OpenATV 8.0.1.
# Only handles the exact audited RC4.1 baseline (before or after modal hotfix).
import hashlib
import os
import re
import shutil
import stat
import sys
import tempfile
from pathlib import Path

base = Path("/usr/lib/enigma2/python/Plugins/Extensions/SATChannelManager")
if len(sys.argv) == 2:
    base = Path(sys.argv[1])
expected = {
    "neo.py": {"18c4556a821dcd2521e3ffc335e5de77efd036a5e618efc7a1c944dec08f9e39"},
    "core.py": {"20efca6edc7921bba0613473d79f2625789027c179d4eda796b9178eacf1c244"},
    "plugin.py": {
        "3383212bb65c22d4e9b7e6f878e53a3adfd8e9c8f8837c6d6237990485db45a3",
        "7bf55830ef35827e278ae32725a2025cbc8b42671e17281655116673665717f1",
    },
}
original = {}
for name in expected:
    path = base / name
    if not path.is_file() or path.is_symlink():
        sys.exit("ERROR: missing or unsafe file: %s" % path)
    data = path.read_bytes()
    original[name] = data
if b"rc4.1-easy" in original["core.py"] and b"def bouquets_menu(" in original["neo.py"]:
    print("Easy Mode already installed. Restart Enigma2 GUI if necessary.")
    sys.exit(0)
for name, data in original.items():
    digest = hashlib.sha256(data).hexdigest()
    if digest not in expected[name]:
        sys.exit("ERROR: %s is not the audited RC4.1 revision; refusing overwrite." % name)

def swap(data, before, after):
    if data.count(before) != 1:
        raise ValueError("Patch anchor missing or duplicated: " + before[:75])
    return data.replace(before, after)

def section(data, first, last, replacement):
    i, j = data.index(first), data.index(last, data.index(first) + len(first))
    return data[:i] + replacement + data[j:]

core = original["core.py"].decode("utf-8")
core = swap(core, "VERSION = '0.4.1-rc4.1-ultrafluid'", "VERSION = '0.4.1-rc4.1-easy'")
marker = "def get_data_plus(source):"
core = swap(core, marker, """def has_world_source(name):
    try:
        get_data(name)
        return True
    except (SatelliteDataError, OSError):
        return False

def has_both_world_sources():
    return all(has_world_source(name) for name in ('oe', 'pli'))


""" + marker)

plugin = original["plugin.py"].decode("utf-8")
if plugin.count("self.items") == 3:
    plugin = plugin.replace("self.items", "self.choice_rows")
elif "self.choice_rows" not in plugin:
    raise ValueError("Unknown SATListView implementation")
plugin = swap(plugin,
    "self['info'] = Label(heading + '\\n%d element(s)' % len(choices))",
    "self['info'] = Label('Choisir une action avec OK')")

neo = original["neo.py"].decode("utf-8")
neo = swap(neo,
    "        self._world_fallback = False\n",
    "        self._world_fallback = False\n        self._pending_smart_mode = None\n")
neo = swap(neo,
    "        self['key_green'] = Label('VERT  Smart Install / Scan')\n        self['key_yellow'] = Label('JAUNE  Gestion / Outils')\n        self['key_blue'] = Label('BLEU  Sources')",
    "        self['key_green'] = Label('VERT  MAJ / Scan')\n        self['key_yellow'] = Label('JAUNE  Mes bouquets')\n        self['key_blue'] = Label('BLEU  Options')")
neo = swap(neo,
    "             'green': self.install_menu, 'yellow': self.tools_menu,\n             'blue': self.sources_menu, 'menu': self.tools_menu,",
    "             'green': self.install_menu, 'yellow': self.bouquets_menu,\n             'blue': self.tools_menu, 'menu': self.tools_menu,")
neo = swap(neo, "'9': self.backup_now, '0': self.smart_menu",
                 "'9': self.backup_now, '0': self.smart_shortcut")
neo = neo.replace("core.has_cached_world_catalog()", "core.has_both_world_sources()")
neo = section(neo, "    def _auto_sync_done(self, result):\n",
              "    @staticmethod\n    def _load_catalog_worker(",
"""    def _auto_sync_done(self, result):
        self._auto_syncing = False
        if self._closed:
            return
        if self.source in ('multi', 'oe', 'pli'):
            self.load_catalog()
        if self._pending_smart_mode is not None:
            mode = self._pending_smart_mode
            self._pending_smart_mode = None
            if core.has_both_world_sources():
                self.smart_installation(mode)
            else:
                missing = ', '.join(x for x in ('oe', 'pli') if not core.has_world_source(x))
                self._error('Donnees satellites indisponibles : %s. Verifier Internet puis BLEU > Actualiser.' % missing)
        elif core.has_both_world_sources():
            self.status('Sources pretes. VERT pour mise a jour ou scan.')
        else:
            self.status('Catalogue incomplet. BLEU > Actualiser les donnees.')

    def _auto_sync_failed(self, failure):
        self._auto_syncing = False
        if self._closed:
            return
        requested = self._pending_smart_mode is not None
        self._pending_smart_mode = None
        message = 'Telechargement satellite impossible : %s' % failure.getErrorMessage()
        if requested:
            self._error(message + '. Aucune modification effectuee.')
        else:
            self.status(message + '. Catalogue local accessible.')

""")
neo = swap(neo,
    "self['righthint'].setText('1  Filtrer les satellites\\n2  Cocher les satellites configures\\n3  Effacer / 5 Rechercher / 9 Backup')",
    "self['righthint'].setText('OK : cocher / decocher\\n5 : rechercher / 1 : filtrer\\nVERT : frequences / scan\\nJAUNE : bouquets')")
neo = section(neo, "    def sources_menu(self):\n", "    def source_action(self, action):\n",
"""    def sources_menu(self):
        if self.busy:
            return
        self.open_chooser('Choisir une source SAT', [
            ('Catalogue mondial OE-Alliance + OpenPLi', ('choose', 'multi')),
            ('OE-Alliance uniquement', ('choose', 'oe')),
            ('OpenPLi uniquement', ('choose', 'pli')),
            ('Satellites de mon OpenATV', ('choose', 'local')),
            ('Fichier XML importe', ('choose', 'import')),
        ], 'BLEU > Actualiser les donnees pour telecharger les catalogues.', self.source_action)

""")
neo = section(neo, "    def install_menu(self):\n", "    def run_action(self, action):\n",
"""    def smart_shortcut(self):
        self.smart_installation('selected' if self.selected else 'preset')

    def install_menu(self):
        if self.busy:
            return
        rows = []
        if self.selected:
            rows.append(('Mettre a jour mes %d satellites coches (fusion)' % len(self.selected), 'smart_selected'))
        rows.extend([
            ('Mettre a jour Nilesat / Badr / Hot Bird / Astra', 'smart'),
            ('Mettre a jour les frequences de 75W a 150E', 'smart_range'),
            ('Rechercher les chaines du satellite (scan tuner)', 'scan_current'),
        ])
        self.open_chooser('Installer - choix simples', rows,
                          'Fusion de FREQUENCES, apercu, confirmation et backup.', self.run_action)

    def bouquets_menu(self):
        if self.busy:
            return
        self.open_chooser('Mes bouquets', [
            ('Creer ou modifier un bouquet TV', 'bouquet_tv'),
            ('Creer ou modifier un bouquet Radio', 'bouquet_radio'),
            ('Sauvegarder mes chaines et favoris', 'backup'),
        ], 'Sport, Films, Musique et autres categories.', self.run_action)

    def tools_menu(self):
        if self.busy:
            return
        self.open_chooser('Options - menu simple', [
            ('Actualiser les donnees satellites', 'update_all'),
            ('Choisir la source SAT', 'sources'),
            ('Rechercher un satellite', 'search'),
            ('Sauvegarde et restauration', 'backup_menu'),
            ('Options avancees', 'advanced_menu'),
        ], 'Les reglages techniques restent dans Options avancees.', self.run_action)

    def backup_menu(self):
        self.open_chooser('Sauvegardes', [
            ('Sauvegarder mes chaines et favoris', 'backup'),
            ('Restaurer une sauvegarde', 'restore'),
        ], 'Aucune restauration sans confirmation.', self.run_action)

    def advanced_menu(self):
        self.open_chooser('Options avancees', [
            ('Scanner plusieurs satellites', 'scan_selected'),
            ('Scanner une frequence precise', 'preview'),
            ('Options du tuner et du scan', 'advanced'),
            ('FUSION / CONSERVER / REMPLACER', 'policy'),
            ('Importer les frequences des SAT coches', 'xml'),
            ('Selectionner les SAT de 75W a 150E', 'range'),
            ('Selectionner tous les satellites', 'all'),
            ('Selectionner les satellites configures', 'configured'),
            ('Effacer la selection', 'clear'),
            ('Aide', 'help'),
        ], 'Operations avancees avec confirmation.', self.run_action)

""")
neo = swap(neo,
    "        elif action == 'sources':\n            self.sources_menu()",
    "        elif action == 'sources':\n            self.sources_menu()\n"
    "        elif action == 'update_all':\n            self.source_action(('download', 'multi'))\n"
    "        elif action == 'backup_menu':\n            self.backup_menu()\n"
    "        elif action == 'advanced_menu':\n            self.advanced_menu()")
neo = section(neo, "    def smart_installation(self, mode='preset'):\n", 
              "        positions = (core.SMART_DEFAULT_POSITIONS",
"""    def smart_installation(self, mode='preset'):
        if mode not in ('preset', 'selected', 'range'):
            return
        if self.busy:
            self.status('Une operation est deja en cours.')
            return
        if self._auto_syncing:
            self._pending_smart_mode = mode
            self.status('Telechargement en cours. Apercu automatique ensuite.')
            return
        if not core.has_both_world_sources():
            self._pending_smart_mode = mode
            self._auto_syncing = True
            self.status('Telechargement automatique OE-Alliance et OpenPLi...')
            task = deferToThread(core.download_all)
            task.addCallbacks(self._auto_sync_done, self._auto_sync_failed)
            return
""")
for name, value in (("core.py", core), ("plugin.py", plugin), ("neo.py", neo)):
    compile(value, str(base / name), "exec")
    original[name] = value.encode("utf-8")
for name, data in original.items():
    path = base / name
    backup = path.with_name(path.name + ".bak-before-easy-ui")
    if not backup.exists():
        shutil.copy2(path, backup)
    fd, tmp = tempfile.mkstemp(prefix=".sat-easy-", dir=str(base))
    try:
        with os.fdopen(fd, "wb") as h:
            h.write(data)
            h.flush()
            os.fsync(h.fileno())
        os.chmod(tmp, stat.S_IMODE(os.stat(path).st_mode))
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)
print("Easy Mode installed successfully. Restart Enigma2 GUI.")
print("Backup of original Python files: *.bak-before-easy-ui")
