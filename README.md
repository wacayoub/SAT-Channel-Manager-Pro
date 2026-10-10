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


## Easy Mode (interface simplifiée via SSH)
- **VERT** : mises à jour des fréquences ou scan tuner (3 à 4 actions).
- **JAUNE** : bouquets TV, radio et sauvegardes (3 actions).
- **BLEU** : actualiser les données, sources, recherche, sauvegardes, options avancées (5 actions).
- **OK** : cocher/décocher un satellite ; **0** : lancement direct de Smart Installation.

Smart Installation télécharge automatiquement les catalogues manquants OE-Alliance et OpenPLi en arrière-plan. Un échec annule l'installation sans écriture. La sécurité historique est conservée : aperçu, confirmation, sauvegarde vérifiée, fusion non destructive.

Le script install.sh vérifie le paquet IPK RC4.1 puis applique easy-mode-rc4.1.py après validation de son empreinte Git. La version opkg reste 0.4.1 ; le correctif modifie les fichiers Python et crée des backups .bak-before-easy-ui. Une version de code inconnue sera refusée.

Commande d'installation SSH :
    wget -O /tmp/install-sat.sh https://raw.githubusercontent.com/wacayoub/SAT-Channel-Manager-Pro/main/install.sh
    sh /tmp/install-sat.sh

Limitation : RC4.1 Easy Mode fusionne les fréquences ; il n'importe pas directement les services TV depuis les sites LyngSat/KingOfSat/FlySat. Validation matérielle OpenATV 8.0.1 encore nécessaire.


## Correctif Neo Icons (10 octobre 2026)
L'installateur `install.sh` applique maintenant le correctif `neo-icons-easy-rc4.1.py` **apres** Easy Mode :
- Trois icones natives Enigma2 en bas de l'ecran : Frequences/Scan, Mes bouquets, Options.
- La touche `0` choisit toujours le preset Nilesat 7W / Badr 26E / Hot Bird 13E / Astra 19.2E, meme si un autre satellite est deja coche.
- VERT met la selection de 4 satellites en premier ; les satellites coches restent un choix distinct.
- Le menu et l'apercu distinguent les **transpondeurs** (`satellites.xml`) des **chaines TV**.

**Important :** "0 nouveau TP" dans l'apercu n'est pas une erreur de telechargement : il peut s'agir de frequences deja presentes. Le telechargement des services TV directement depuis LyngSat / FlySat / KingOfSat n'est **pas encore implemente** ; pour ajouter effectivement des services TV aujourd'hui, choisir le scan DVB d'un satellite configure sur le tuner.

Cette mise a jour d'interface ne change pas `lamedb`, les bouquets ou la configuration tuner. Elle conserve les copies des fichiers Python avant modification. A valider sur un vrai recepteur OpenATV 8.0.1.
