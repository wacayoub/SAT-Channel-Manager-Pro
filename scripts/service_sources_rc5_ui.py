# -*- coding: utf-8 -*-
"""RC5.1 Enigma2 add-on: explicit BLUE/GREEN menu TV online preview.

No automatic background requests on zap/navigation; native Enigma2 UI remains
responsive, and no lamedb/bouquet/service import is performed.
"""
import functools

from . import service_sources_rc5


def attach_home(home_class):
    if getattr(home_class, "_satcm_rc5_tv_index_attached", False):
        return home_class
    old_install = getattr(home_class, "install_menu", None)
    old_action = getattr(home_class, "run_action", None)
    if not callable(old_install) or not callable(old_action):
        return home_class

    @functools.wraps(old_install)
    def install_menu(self):
        if self.busy:
            return
        rows = [
            ("1. FREQUENCES : Nilesat / Badr / Hot Bird / Astra", "smart"),
        ]
        if self.selected:
            rows.append(
                ("2. FREQUENCES : mes %d SAT coches" % len(self.selected),
                 "smart_selected")
            )
        rows.extend((
            ("3. FREQUENCES : 75W a 150E", "smart_range"),
            ("4. CHAINES TV ONLINE : source reelle / apercu (sans importer)", "online_tv"),
            ("5. CHAINES TV : scan tuner DVB-S2", "scan_current"),
        ))
        return self.open_chooser(
            "FREQUENCES ET CHAINES TV : deux sources distinctes", rows,
            "ONLINE = affiche les vrais services du catalogue externe. "
            "Aucun ecrasement des favoris / pas d'import automatique.",
            self.run_action
        )

    @functools.wraps(old_action)
    def run_action(self, action):
        if action != "online_tv":
            return old_action(self, action)
        if self.busy:
            self.status("Operation en cours, patienter.")
            return
        # Include primary Morocco/satellite footprint even if only one
        # unrelated SAT was checked before entering the menu.
        positions = list(service_sources_rc5.DEFAULT_POSITIONS)
        highlighted = self.current_position()
        if highlighted is not None and highlighted not in positions:
            positions.append(highlighted)
        for pos in sorted(self.selected):
            if pos not in positions and len(positions) < 12:
                positions.append(pos)
        self.busy = True
        self.status("Chargement de vraies chaines TV (catalogue Enigma2 HTTPS)...")
        from twisted.internet.threads import deferToThread
        task = deferToThread(service_sources_rc5.source_status, tuple(positions))
        def ok(result):
            self.busy = False
            if getattr(self, "_closed", False):
                return
            self.status("Catalogue de services TV charge : aucun fichier modifie.")
            from Screens.MessageBox import MessageBox
            self.session.open(
                MessageBox, service_sources_rc5.text_report(result),
                MessageBox.TYPE_INFO)
        def fail(failure):
            self.busy = False
            if getattr(self, "_closed", False):
                return
            self._error(
                "Catalogue TV externe indisponible; aucun changement : %s" %
                str(failure.getErrorMessage())[:160])
        task.addCallbacks(ok, fail)

    home_class.install_menu = install_menu
    home_class.run_action = run_action
    home_class._satcm_rc5_tv_index_attached = True
    return home_class
