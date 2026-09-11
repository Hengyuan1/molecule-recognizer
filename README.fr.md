# Molecule Recognizer

[English](README.md) | [简体中文](README.zh-CN.md) | [한국어](README.ko.md) | [Русский](README.ru.md) | Français

Reconnaissez des structures moléculaires dans des captures d’écran, des articles et des pages web, convertissez-les en SMILES, corrigez-les dans un éditeur interactif et générez des coordonnées 3D à enregistrer ou à copier au format XYZ. L’application est conçue pour les travaux de chimie computationnelle.

**Version [0.3.0](https://github.com/Hengyuan1/molecule-recognizer/releases/tag/v0.3.0)** — Application Windows portable avec OSRA intégrée, et application Linux/Python. [Télécharger pour Windows](https://github.com/Hengyuan1/molecule-recognizer/releases/download/v0.3.0/MolRecognizer-0.3.0-windows-x64.zip).

![MolRecognizer avec l’image source, la structure 2D modifiable et le modèle 3D affiché côte à côte](docs/media/UI-demo.png)

Double-cliquez sur l’aperçu 3D généré pour le comparer à la structure 2D. Faites glisser le séparateur pour régler la largeur des panneaux ; l’éditeur et la ligne SMILES restent utilisables.

Ce guide couvre l’installation et l’utilisation courante. Les détails des fonctionnalités, du développement et des versions sont disponibles dans le [README anglais](README.md) et les documents liés ci-dessous. Seule la documentation est traduite : les boutons et menus de l’application restent en anglais, et leurs noms sont donc conservés dans les instructions.

## Accès rapide

- [Utilisation sous Windows](#utilisation-sous-windows)
- [Utilisation sous Linux](#utilisation-sous-linux)
- [OSRA et dépendances optionnelles](#osra-et-dépendances-optionnelles)
- [Reconnaître, modifier et exporter](#reconnaître-modifier-et-exporter)
- [Raccourcis clavier](#raccourcis-clavier) · [API Python](#api-python) · [Dépannage](#dépannage)

## Utilisation sous Windows

### EXE portable : sans installer Python, Conda ou WSL

1. Téléchargez [MolRecognizer-0.3.0-windows-x64.zip](https://github.com/Hengyuan1/molecule-recognizer/releases/download/v0.3.0/MolRecognizer-0.3.0-windows-x64.zip) (159 Mio).
2. Extrayez **l’intégralité du ZIP** dans un dossier permanent, accessible en écriture et avec un chemin court, par exemple `C:\Users\YourName\Apps`. Évitez les dossiers trop profondément imbriqués.
3. Ouvrez `MolRecognizer.exe` dans le dossier `MolRecognizer` extrait.
4. Conservez `_internal`, `tools`, l’EXE du processus de travail et tous les fichiers associés ensemble. **Ne déplacez pas uniquement l’EXE principal et ne l’exécutez pas depuis le ZIP.** Vous pouvez créer un raccourci vers cet EXE sur le Bureau.

Configuration cible : **Windows 10/11 x64**, avec .NET Framework 4.x pour la capture d’écran. Le paquet contient **OSRA 2.2.4**, ses dictionnaires et DLL, l’environnement Python/Qt/RDKit et un outil de capture précompilé. Aucune installation séparée d’OSRA ni exécution de scripts PowerShell n’est nécessaire pour la version portable. MolScribe et les poids de son modèle ne sont pas inclus.

Pour une mise à jour, fermez l’application, extrayez la nouvelle version dans un autre dossier, testez-la puis modifiez la cible du raccourci. Ne mélangez pas les fichiers de plusieurs versions.

### Différence entre les téléchargements et sécurité

- `MolRecognizer-0.3.0-windows-x64.zip` : l’application Windows prête à l’emploi. C’est le fichier à télécharger pour une utilisation normale.
- `MolRecognizer-0.3.0-sources.zip` : le code source de **la même version**, de ses dépendances, ainsi que les correctifs et instructions de compilation. Il s’adresse aux développeurs ; ce n’est pas une ancienne version et il n’est pas nécessaire pour exécuter l’application.
- `.zip.sha256` : l’empreinte du ZIP correspondant, pour vérifier qu’il n’a pas été endommagé ou modifié.
- Les archives « Source code » générées automatiquement par GitHub ne sont pas l’application Windows et ne remplacent pas le `sources.zip` contenant les sources des dépendances.

Ouvrez PowerShell dans le dossier contenant le ZIP et son fichier d’empreinte :

```powershell
Get-FileHash .\MolRecognizer-0.3.0-windows-x64.zip -Algorithm SHA256
Get-Content .\MolRecognizer-0.3.0-windows-x64.zip.sha256
```

Comparez les valeurs SHA-256. Une correspondance n’est ni une signature numérique ni une garantie de sécurité. L’application n’est pas signée ; Windows peut donc afficher un avertissement. Vérifiez la provenance du téléchargement et **ne désactivez pas l’antivirus ni ne contournez les règles de sécurité de votre organisation**.

Les ZIP publiés sont identiques aux fichiers testés. Certains documents internes conservent la mention « not published » datant de la compilation ; la publication ultérieure est indiquée sur la [page de la version](https://github.com/Hengyuan1/molecule-recognizer/releases/tag/v0.3.0). Le tag `v0.3.0` identifie les sources exactes de la compilation, tandis que `main` contient aussi des mises à jour ultérieures de la documentation.

### Exécuter les sources dans PowerShell

Ignorez cette section si vous utilisez l’EXE portable. Python natif sous Windows ou un environnement Conda autorisé sur votre ordinateur professionnel suffit : WSL n’est pas nécessaire.

Installez Git et uv si besoin :

```powershell
winget install --id Git.Git -e
winget install --id astral-sh.uv -e
```

Rouvrez PowerShell puis récupérez les sources :

```powershell
git clone --branch main https://github.com/Hengyuan1/molecule-recognizer.git
cd molecule-recognizer
```

Sans Git, téléchargez le ZIP des sources de la branche `main`, extrayez-le et placez-vous dans le dossier contenant `pyproject.toml`. Choisissez une méthode d’installation.

**Option A — outil uv en mode éditable, accessible depuis n’importe quel dossier.**

```powershell
uv tool install --python 3.11 --editable .
uv tool update-shell
```

Rouvrez PowerShell et lancez :

```powershell
molrecognizer
```

Conservez le dossier des sources : l’installation éditable l’utilise directement. Si vous le déplacez, réinstallez l’outil depuis son nouvel emplacement.

**Option B — Conda / Miniconda.**

```powershell
conda create -n molrecognizer python=3.11 -y
conda activate molrecognizer
python -m pip install -e .
molrecognizer
```

Dans les prochains terminaux, exécutez d’abord `conda activate molrecognizer`, puis `molrecognizer`.

**Pour le développement :** au lieu d’installer un outil, utilisez `uv sync --python 3.11`, puis `uv run molrecognizer` depuis le dépôt.

### Configurer OSRA pour l’installation Windows depuis les sources

L’installation des sources **n’installe pas OSRA automatiquement**. Utilisez un environnement d’exécution Windows OSRA complet, ou le dossier `MolRecognizer\tools\osra` d’une application portable déjà extraite. Gardez les DLL, dictionnaires et autres fichiers ensemble. Pour compiler OSRA, consultez le [guide de compilation](packaging/windows/OSRA-BUILD.md) en anglais.

Dans la session PowerShell courante, indiquez le chemin réel de l’exécutable :

```powershell
$env:OSRA_EXECUTABLE = "C:\path\to\OSRA\bin\osra.exe"
& $env:OSRA_EXECUTABLE --version
molrecognizer
```

Pour réutiliser l’OSRA du paquet portable, le chemin se termine par `MolRecognizer\tools\osra\bin\osra.exe`. Pour enregistrer le réglage pour les sessions suivantes :

```powershell
[Environment]::SetEnvironmentVariable(
    "OSRA_EXECUTABLE",
    "C:\path\to\OSRA\bin\osra.exe",
    "User"
)
```

Rouvrez ensuite PowerShell. Vous pouvez aussi limiter la configuration à un environnement Conda :

```powershell
conda activate molrecognizer
conda env config vars set OSRA_EXECUTABLE="C:\path\to\OSRA\bin\osra.exe"
conda deactivate
conda activate molrecognizer
```

### Capture et mise à l’échelle sous Windows

Gardez le focus clavier dans MolRecognizer, placez le pointeur sur l’écran du portable ou le moniteur externe souhaité, puis appuyez sur **Alt+Y** ou **Ctrl+Shift+S**. Tracez un rectangle ; vous pouvez le déplacer ou ajuster ses bords et coins. **Entrée / Recognize** lance la reconnaissance ; **Échap / clic droit / Cancel** annule. Les flèches déplacent la zone d’un pixel, ou de dix avec Maj. Le bouton **Screenshot** est également disponible.

Sous Windows natif, ces raccourcis **ne sont pas globaux** : l’application doit avoir le focus clavier. Un seul moniteur est capturé à la fois. Pour en changer, annulez, déplacez le pointeur et recommencez.

La version portable utilise l’outil précompilé. L’installation Python compile un assistant C# avec Windows PowerShell et `Add-Type`, ce que les politiques d’entreprise peuvent bloquer. Snipaste n’est pas nécessaire. Si la capture est bloquée, enregistrez une image avec un outil autorisé puis ouvrez-la avec **Open Image**.

L’ajustement automatique intervient après le déplacement entre moniteurs. Les commandes **A− / A+** en bas à droite règlent la taille de l’interface ; cliquez sur le pourcentage pour rétablir l’échelle recommandée de l’écran, ou sur **Fit** pour réadapter la taille de la fenêtre. Les réglages sont mémorisés par moniteur.

### Facultatif : WSL2 / WSLg

WSL est une autre façon d’utiliser l’application Linux, **pas une obligation pour l’EXE Windows ou Conda**. Utilisez-le uniquement là où il est autorisé.

Dans Ubuntu/WSL2 avec WSLg, suivez les instructions Linux ci-dessous pour installer **OSRA et Python/uv pour Linux dans WSL**, puis lancez `molrecognizer` depuis le terminal Ubuntu. Ne configurez pas l’application Linux avec un fichier Windows `osra.exe`.

WSLg fournit un **raccourci Windows global Alt+Y** pendant que l’application fonctionne, si l’assistant Windows peut démarrer et qu’aucune autre application n’a réservé cette combinaison. La capture utilise le moniteur Windows sous le pointeur. L’interopérabilité PowerShell et l’autorisation d’exécuter l’assistant sont nécessaires. Les menus et la comparaison des nouvelles reconnaissances restent dans la fenêtre principale sous WSLg pour limiter les problèmes de fenêtres contextuelles.

## Utilisation sous Linux

La version Linux est une application Python utilisant OSRA localement et nécessitant une session graphique. Ces exemples Bash ciblent Ubuntu/Debian ; adaptez les paquets aux autres distributions.

### Installer OSRA

Pour les distributions proposant un paquet OSRA :

```bash
sudo apt update
sudo apt install git osra
osra --version
```

La disponibilité et la version dépendent de la distribution et peuvent différer d’OSRA 2.2.4 incluse sous Windows. Si vous disposez déjà d’une installation fonctionnelle, vous pouvez la conserver. Exemple de chemin personnalisé :

```bash
export OSRA_EXECUTABLE="/path/to/OSRA/bin/osra"
"$OSRA_EXECUTABLE" --version
```

Remplacez le chemin par le vôtre. Pour les futurs terminaux, ajoutez la ligne `export` à `~/.bashrc` ou au fichier de démarrage de votre shell. Sans paquet approprié, obtenez les sources et instructions auprès du [projet OSRA](https://sourceforge.net/projects/osra/).

### Installer et lancer MolRecognizer

**Python 3.10 ou ultérieur** est requis ; les exemples utilisent 3.11. Pour la méthode uv, commencez par [installer uv](https://docs.astral.sh/uv/getting-started/installation/), puis récupérez les sources :

```bash
git clone --branch main https://github.com/Hengyuan1/molecule-recognizer.git
cd molecule-recognizer
```

**Option A — outil uv en mode éditable.**

```bash
uv tool install --python 3.11 --editable .
uv tool update-shell
```

Ouvrez un nouveau terminal ; aucune activation d’environnement n’est nécessaire et vous pouvez lancer depuis n’importe quel dossier :

```bash
molrecognizer
```

Conservez le dossier des sources. Réinstallez l’outil si vous le déplacez.

**Option B — pip dans un environnement virtuel.** Python 3.10+ et la prise en charge de `venv` doivent être installés.

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e .
molrecognizer
```

Dans les terminaux suivants, activez d’abord le même environnement :

```bash
source /path/to/molecule-recognizer/.venv/bin/activate
molrecognizer
```

**Pour le développement :** utilisez `uv sync --python 3.11` puis `uv run molrecognizer` dans le dépôt. Depuis un autre dossier :

```bash
uv run --project /path/to/molecule-recognizer molrecognizer
```

### Capture d’écran sous Linux

Gardez le focus dans l’application, placez le pointeur sur l’écran cible et utilisez **Alt+Y / Ctrl+Shift+S**. La sélection Qt sans bordure permet de dessiner, déplacer et redimensionner la zone ; Entrée confirme, Échap annule. Linux natif n’enregistre pas de raccourci global de capture.

- **X11 :** Qt est essayé en premier et ne nécessite généralement aucun paquet supplémentaire. `scrot` est une solution de secours optionnelle.
- **Wayland :** le résultat dépend des autorisations du bureau et du compositeur. `grim` fonctionne sur des compositeurs compatibles, mais n’est pas une solution universelle pour Wayland. L’application essaie aussi `gnome-screenshot` s’il est installé.
- Si la capture échoue, produit un écran noir ou affiche le mauvais contenu, utilisez l’outil de capture du bureau puis chargez l’image enregistrée avec **Open Image**.

Installez uniquement l’outil de secours adapté :

```bash
# Solution de secours X11
sudo apt install scrot

# Compositeur Wayland compatible
sudo apt install grim
```

Sous WSLg, reportez-vous plutôt aux instructions de capture Windows de la section WSLg ci-dessus.

## OSRA et dépendances optionnelles

L’installation depuis les sources installe automatiquement RDKit, PySide6, Pillow et NumPy (`numpy<2`) ; consultez [pyproject.toml](pyproject.toml). OSRA est un exécutable natif distinct, pas un paquet Python wheel : `pip` et `uv sync` ne l’installent pas. L’application Windows portable le contient déjà.

Une variable `OSRA_EXECUTABLE` explicite est toujours prioritaire et doit désigner un programme fonctionnel. Sans cette variable :

- **Windows portable :** recherche dans `tools/osra/bin` à côté de l’EXE, puis `.tools/osra/bin`, puis `PATH`.
- **Installation Python depuis les sources :** recherche dans `PATH`, puis `.tools/osra/bin` et `tools/osra/bin` dans le projet.

Exemple d’installation locale au projet ; sous Windows, remplacez `osra` par `osra.exe` :

```text
.tools/osra/
├── bin/
│   ├── osra
│   └── bibliothèques nécessaires et autres fichiers
└── share/
    ├── chain.txt
    ├── spelling.txt
    └── superatom.txt
```

Si les trois dictionnaires sont présents dans `share/osra`, `share` ou `bin` de l’installation OSRA choisie, l’application transmet automatiquement leurs chemins absolus. Elle ne dépend donc pas du dossier courant. Conservez également tous les autres fichiers d’exécution.

### Moteur MolScribe facultatif

Choisissez la commande correspondant à l’environnement réellement utilisé :

```bash
# Environnement de développement uv
uv sync --extra molscribe

# Outil uv éditable : depuis les sources
uv tool install --python 3.11 --editable --with molscribe --with huggingface-hub .

# Environnement pip / Conda activé
python -m pip install -e ".[molscribe]"
```

Installer ces dépendances ne remplace pas OSRA comme moteur par défaut. Dans l’API Python, indiquez explicitement `backend="molscribe"`. Les poids du modèle peuvent être téléchargés à la première utilisation. Le mode GPU requiert aussi une version compatible de PyTorch avec CUDA. Cela n’ajoute pas MolScribe à un EXE portable déjà compilé.

## Reconnaître, modifier et exporter

1. Utilisez **Open Image** ou la capture d’écran pour une seule molécule. **Load SMILES** fonctionne sans OSRA.
2. Comparez le dessin 2D et le SMILES à l’original : vérifiez les étiquettes atomiques, la fermeture des cycles, les ordres de liaison, les charges et la stéréochimie. Une vérification de valence réussie ne prouve pas que la reconnaissance est correcte. Si l’image contient plusieurs structures, le premier résultat valide est chargé.
3. Corrigez manuellement avec les outils ou comparez des alternatives via **Retry recognition**. Undo/Redo conserve la connectivité et les informations stéréochimiques.
4. Cliquez sur **Render** pour générer les coordonnées 3D. Un double-clic sur l’aperçu ouvre la comparaison côte à côte ; le séparateur règle la largeur. En 3D, glissez avec le bouton gauche pour tourner, avec le droit pour déplacer, et utilisez la molette pour zoomer.
5. Après une modification 2D, cliquez de nouveau sur **Render** pour actualiser la 3D.
6. **Copy / Export** concernent les SMILES ; **Save xyz / Copy xyz** enregistrent ou copient tout le texte XYZ. Les menus permettent de choisir Angstrom (Å, par défaut) ou Bohr.

**View → Fit structure** ajuste seulement la vue 2D, sans modifier les coordonnées ni la position des liaisons. **Format** recalcule la disposition 2D ; **Clean** vide l’espace de travail. Le bouton **Fit** en bas à droite adapte la fenêtre elle-même : ces opérations sont distinctes.

### Réessayer la reconnaissance des structures complexes

Après la fin ou l’échec de la première reconnaissance, utilisez **Retry recognition**. Trois variantes OSRA locales sont comparées à partir de l’image en pleine résolution : seuillage adaptatif, interprétation à 100 dpi et seuil de gris 0.35. Les scores ne sont pas des pourcentages de précision et ne sélectionnent aucun résultat automatiquement.

Cliquez sur **Use selected** uniquement pour remplacer la structure actuelle. **Keep current / Échap** conserve vos modifications. **Stop retries** arrête les nouvelles tentatives mais garde les candidats déjà calculés. Le remplacement peut être annulé en une seule opération Undo. Après acceptation, refaites Render avant l’export XYZ.

Chaque tentative est limitée à 15 secondes de traitement OSRA plus un délai de grâce de 10 secondes pour le processus, soit jusqu’à 75 secondes pour les trois ; vous pouvez annuler à tout moment. Tous les candidats peuvent être erronés. Une capture plus nette du PDF ou dessin vectoriel original apporte généralement davantage d’informations que l’agrandissement d’un petit PNG.

### Outils et affichage

- **Select :** cliquez sur un atome pour changer d’élément, faites-le glisser pour le déplacer ; tracez une sélection dans le vide et déplacez-la en groupe. Cliquez sur une liaison pour faire défiler son ordre.
- **Bond :** choisissez Single/Double/Triple/Wedge/Dash. Cliquez sur un atome pour ajouter un atome lié ou faites glisser depuis un atome pour créer une liaison. Les coins pleins et hachurés représentent la stéréochimie.
- **Atom / Eraser :** ajouter ou remplacer des atomes / supprimer des atomes et liaisons, y compris une sélection entière.
- **Ring :** ajouter un benzène ou un cycle à 6, 5, 4 ou 3 atomes sur un atome, une liaison ou dans le vide ; glisser pour orienter.
- **Charge ⊕/⊖ / PT :** régler la charge formelle / choisir un élément dans le tableau périodique.
- **Undo / Redo :** annuler et restaurer les atomes, liaisons, connexions, coordonnées et marques stéréochimiques.
- Les cycles aromatiques sont affichés sous forme de Kekulé, avec liaisons simples et doubles. Les groupes O–H et N–H ordinaires s’affichent sous forme compacte OH, NH, NH₂, etc., sans modifier les données moléculaires ni les SMILES. Les hydrogènes isotopiques, mappés, chargés ou associés à une marque stéréochimique restent explicites.
- Les coordonnées 2D, l’affectation des liaisons simples/doubles et les coins reconnus par OSRA sont conservés pour faciliter la comparaison. Les erreurs doivent toujours être corrigées manuellement. Format recalcule la disposition et contrôle les informations stéréochimiques, sans remplacer la vérification de la reconnaissance.
- Sur le canevas 2D, la molette zoome et un glissement avec le bouton du milieu ou droit déplace la vue. Fermer la comparaison 3D rétablit le canevas 2D complet.

## Raccourcis clavier

| Action | Raccourci |
| --- | --- |
| Ouvrir une image | Ctrl+O |
| Capture d’écran | Ctrl+Shift+S / Alt+Y |
| Exporter les SMILES | Ctrl+E |
| Annuler / rétablir | Ctrl+Z / Ctrl+Shift+Z |
| Quitter | Ctrl+Q |
| Supprimer la sélection | Delete / Backspace |
| Agrandir / réduire l’interface | Ctrl+Alt++ / Ctrl+Alt+- |
| Réinitialiser l’échelle de l’interface | Ctrl+Alt+0 |

Sous Windows et Linux natifs, la capture nécessite le focus dans l’application. Seul l’assistant WSLg décrit plus haut fournit Alt+Y globalement. Sur un clavier français, Shift correspond à Maj, Delete à Suppr et Backspace à Retour arrière.

## Confidentialité et fichiers temporaires

La reconnaissance s’effectue localement, sans envoi d’images au site NCI OSRA. L’outil Windows conserve l’écran et la sélection en mémoire, sans fichier de capture. Les outils de secours en ligne de commande Linux peuvent créer un PNG temporaire, supprimé après lecture. Les images temporaires nécessaires à la reconnaissance sont supprimées après traitement.

L’image originale reste en mémoire pour Retry recognition jusqu’à son remplacement, l’effacement de l’espace de travail ou la fermeture de l’application. Les tentatives utilisent les pixels originaux, pas la miniature. Leur PNG temporaire est supprimé en cas de réussite, d’échec ou d’annulation.

## API Python

Ces exemples s’utilisent dans un environnement où le paquet Python et le moteur de reconnaissance sont installés, pas directement dans l’EXE :

```python
import molrecognizer

# Obtenir des SMILES ou une molécule avec ses coordonnées
smiles = molrecognizer.recognize("molecule.png")
mol = molrecognizer.recognize_to_molecule("molecule.png")
print(smiles, mol.num_atoms, mol.num_bonds)

# Conversion des SMILES et contrôle de valence
mol = molrecognizer.smiles_to_molecule("CCO")
print(molrecognizer.molecule_to_smiles(mol))
print(molrecognizer.check_valence(mol))
```

Mode GPU MolScribe facultatif :

```python
smiles = molrecognizer.recognize(
    "molecule.png", backend="molscribe", device="cuda"
)
```

Pour d’autres exemples de modification programmatique des molécules, consultez l’[API en anglais](README.md#python-api).

## Dépannage

- **Commande `molrecognizer` introuvable :** pour uv, lancez `uv tool update-shell` puis rouvrez le terminal ; pour Conda/venv, activez le bon environnement. Sous Linux, vérifiez le chemin avec `command -v molrecognizer`.
- **OSRA introuvable :** sous Windows, vérifiez `$env:OSRA_EXECUTABLE` et `Get-Command osra.exe` ; sous Linux, `command -v osra` et `printenv OSRA_EXECUTABLE`. Une ancienne variable peut prendre le pas sur l’OSRA intégrée.
- **Dictionnaire ou DLL manquant :** restaurez le paquet complet et vérifiez `chain.txt`, `spelling.txt` et `superatom.txt`. Ne copiez pas seulement l’EXE.
- **Raccourci de capture inactif :** vérifiez le focus sous Windows/Linux natifs ; sous WSLg, les autorisations de l’assistant et l’utilisation du raccourci par une autre application. Vous pouvez aussi ouvrir une capture issue d’un outil autorisé via Open Image.
- **Interface trop petite ou trop grande :** utilisez **Fit / A− / A+** sur le moniteur concerné.
- **Erreur d’affichage ou de plugin Qt sous Linux :** lancez l’application dans une session graphique ou WSLg fonctionnelle et vérifiez les bibliothèques Qt de votre distribution. Un terminal sans environnement graphique ne peut pas afficher l’interface.
- **Structure incorrecte :** recadrez une seule molécule nette, comparez les candidats et vérifiez manuellement. OSRA présente des erreurs connues de reconnaissance stéréochimique.

Le journal se trouve dans `~/.molrecognizer/molrecognizer.log` sous Linux ou `%USERPROFILE%\.molrecognizer\molrecognizer.log` sous Windows ; il est renouvelé à chaque lancement. Pour [signaler un problème](https://github.com/Hengyuan1/molecule-recognizer/issues), indiquez la version, les étapes et un exemple partageable publiquement. N’envoyez pas d’images de recherche confidentielles ni de journaux privés.

## Tests et documentation de développement

Depuis le dossier des sources :

```bash
# Tests rapides, sans modèle ni OSRA
uv run pytest tests/ -m "not slow"

# Tests MolScribe optionnels : téléchargement possible du modèle au premier lancement
uv run --extra molscribe pytest tests/ -m slow
```

[Fonctionnalités détaillées](README.md#features) · [Structure du projet](README.md#project-structure) · [Historique](CHANGELOG.md) · [Compilation Windows](packaging/windows/README.md) · [Validation de la version](packaging/windows/audits/0.3.0-final/VALIDATION.md) — documents en anglais. Les tests automatiques et les premiers essais du propriétaire ne constituent pas une validation complète sur une machine vierge ni une garantie de précision.

## Licence

Le code de MolRecognizer est sous [licence MIT](LICENSE). Les composants tiers du paquet Windows, dont OSRA, conservent leurs propres licences ; consultez les [mentions tierces](packaging/windows/THIRD-PARTY-NOTICES.md) et **Help → Third-party licenses**. La licence de l’application ne remplace pas leurs conditions.
