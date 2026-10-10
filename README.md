# SAT Channel Manager Pro — RC4.1 (Worldwide Ultra Fluid)

Gestionnaire de transpondeurs satellites pour Enigma2 / OpenATV 8.0.1, destiné notamment au Vu+ Zero 4K.

**Version expérimentale : tests logiciels hors décodeur uniquement.**

## Fonctions RC4.1
- Catalogue mondial indépendant des satellites déjà scannés.
- Sélection multiple et plage **75°W → 150°E** incluse.
- Smart Installation préréglée : **Nilesat 7°W, Badr 26°E, Hot Bird 13°E, Astra 19,2°E**.
- Comparaison/aperçu des fréquences avant validation.
- Fusion non destructive de `satellites.xml`, sauvegarde obligatoire vérifiée.
- Chargement en arrière-plan pour une interface plus fluide.
- Sources de transpondeurs XML : OE-Alliance et OpenPLi.

**Limitations :** RC4.1 ne télécharge pas encore directement les services TV LyngSat, KingOfSat ou FlySat, ne scanne pas automatiquement les chaînes, et ne garantit pas la réception physique d'un satellite.

## Installer directement depuis SSH
Une fois le paquet de version publié dans `packages/` :

```sh
wget -O /tmp/install-sat.sh https://raw.githubusercontent.com/wacayoub/SAT-Channel-Manager-Pro/main/install.sh
sh /tmp/install-sat.sh
```

L'installateur doit vérifier SHA-256 avant d'appeler `opkg install`.
Redémarrer ensuite l'interface Enigma2 via les menus OpenATV.

## Sécurité
Aucune fusion ne doit commencer sans aperçu, confirmation et sauvegarde. Ne pas tester un remplacement avant d'avoir validé l'ouverture et la navigation sur le vrai récepteur.

## Licence
Voir les licences des sources de données utilisées ; le dépôt ne confère pas de droits supplémentaires sur LyngSat/FlySat/KingOfSat.
