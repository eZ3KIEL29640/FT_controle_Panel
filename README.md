# Freqtrade Control Panel (Flask)

Panneau de contrôle **local** pour piloter des tâches Freqtrade depuis un navigateur :

- **Download data** (multi-timeframes prédéfinies)
- **Backtest** (avec sélection de fichier `.json`)
- **Backtest BEAR** (fenêtre fixe `20220110-20220618`)
- **Hyperopt** (epochs + spaces)
- **Apply Strategy Hyperopt** : applique un `.json` optimisé à la stratégie courante en sauvegardant l’ancien sous `BAK_<strategy>_YYYYMMDD_HHMM.json`
- **Git PUSH** : add/commit/push rapide sur un repo au choix (liste lue depuis `git_path.txt`)
- **Logs** : flux temps-réel + fichiers téléchargeables

> ⚠️ Cet outil est prévu pour un usage **local** (127.0.0.1). Ne l’expose pas tel quel sur internet.

---

## Sommaire

1. [Prérequis](#prérequis)  
2. [Installation](#installation)  
3. [Lancement](#lancement)  
4. [Utilisation](#utilisation)  
   - [Strategy](#strategy)  
   - [Backtest](#backtest)  
   - [Hyperopt](#hyperopt)  
   - [Apply Strategy Hyperopt](#apply-strategy-hyperopt)  
   - [Git PUSH](#git-push)  
   - [Logs](#logs)  
5. [Configuration de `git_path.txt`](#configuration-de-git_pathtxt)  
6. [Sécurité & bonnes pratiques](#sécurité--bonnes-pratiques)  
7. [Pagination Git (naviguer dans l’historique)](#pagination-git-naviguer-dans-lhistorique) ✅  
8. [Dépannage rapide](#dépannage-rapide)  
9. [Déploiement Git du projet](#déploiement-git-du-projet)

---

## Prérequis

- Windows (le script privilégie `./.venv/Scripts/python.exe`)
- Python 3.10+  
- **Freqtrade** installé et accessible via `python -m freqtrade`
- Dossier projet avec :
  - `user_data/config_base.json`
  - `user_data/strategies/` (stratégies `.py` et fichiers `.json`)

---

## Installation

1) **Cloner** ce dépôt (ou copier les fichiers dans ton dossier projet).  
2) *(Optionnel mais recommandé)* **Créer un venv** :
```powershell
python -m venv .venv
.\.venv\Scripts\activate
python -m pip install --upgrade pip
```

3) **Installer Flask** :
```powershell
pip install flask
```

4) **Vérifier Freqtrade** :
```powershell
python -m freqtrade --help
```

5) **Créer `git_path.txt`** (optionnel) avec **un chemin de repo Git par ligne** (voir [Configuration](#configuration-de-git_pathtxt)).

---

## Lancement

Dans le dossier où se trouve `app.py` :

```powershell
python app.py
```

Ouvrir : **http://127.0.0.1:5000**

---

## Utilisation

### Strategy
- **Script** : sélectionne la stratégie `.py` dans `user_data/strategies/`.
- **Start / End date** : bornes pour Download/Backtest/Hyperopt (si End vide pour backtest, la date du jour est utilisée).
- Boutons **Download data** et **Logs** sur la **même ligne**.

### Backtest
- Sélectionne un **`.json`** dans `user_data/strategies/`.  
- **Backtest** : remplace **temporairement** `<strategy>.json` par le `.json` choisi, lance le backtest, puis **restaure** les fichiers.  
- **Backtest BEAR** : backtest sur la période fixe `20220110-20220618`.

### Hyperopt
- Paramètre **Epochs** et **Spaces** (règles : `all` exclusif, `default` force buy/sell/roi/stoploss).  
- Sauvegarde `<strategy>.json`, exécute l’hyperopt, **archive** le nouveau `.json` généré sous :
```
<strategy>_<nbJours>_<start>_<end>_<timestamp>.json
```
puis restaure l’original.

### Apply Strategy Hyperopt
- Liste des `.json` (⚠️ **sans** ceux qui commencent par `BAK_`).
- **Apply** :
  1. Sauvegarde l’actuel `user_data/strategies/<strategy>.json` en  
     `user_data/strategies/BAK_<strategy>_YYYYMMDD_HHMM.json`
  2. Remplace `<strategy>.json` par le fichier sélectionné.

> Si tu sélectionnes déjà `<strategy>.json`, l’action est ignorée (avertissement).

### Git PUSH
- Liste lue depuis `git_path.txt`. Le **dernier** chemin listé est **présélectionné**.  
- Action **PUSH** :
```
git add -A
git commit -m "auto push YYYY-MM-DD HH:MM:SS"
git push
```

### Logs
- Chaque action affiche un flux temps-réel et fournit un **lien de log** téléchargeable.
- Page dédiée : **/logs/**

---

## Configuration de `git_path.txt`

- Un chemin **absolu** ou **relatif** par ligne.  
- Lignes vides et celles commençant par `#` ignorées.  
- Le **dernier** chemin listé sera **présélectionné** dans l’UI.

Exemple :
```
C:\Users\me\repos\freqtrade-utils
..\..\another-repo
# commentaire
D:\work\my-strats   <- sera présélectionné
```

---

## Sécurité & bonnes pratiques

- L’app écoute sur `127.0.0.1`. Ne pas exposer sans protection (reverse proxy + auth, etc.).  
- Les actions manipulent des fichiers dans `user_data/strategies/`. Des sauvegardes `BAK_...` sont créées.  
- Versionne tes `.json` optimisés : pousse-les dans Git (voir ci-dessous **Pagination Git**).

---

## Dépannage rapide

- **`python -m freqtrade` introuvable** : active le bon venv, installe freqtrade avec le **même** Python que celui qui lance `app.py`.  
- **Droits/chemins** : vérifie `user_data/strategies/` et les permissions d’écriture.  
- **Git PUSH échoue** : ajoute le dépôt dans `git_path.txt`, assure-toi d’avoir les droits d’écriture, configure le remote (`git remote -v`).  
- **Restauration Backtest** : les swaps sont loggés ; voir `/logs/`.

---

## Déploiement Git du projet

Initialisation :
```bash
git init
git add app.py README.md
git commit -m "feat: Freqtrade control panel with hyperopt/backtest/apply/git"
```

Remote :
```bash
git branch -M main
git remote add origin <URL_DU_REPO>
git push -u origin main
```

Mises à jour :
```bash
git add -A
git commit -m "chore: updates"
git push
```

---

**Bon trading & bonnes optimisations !** 🚀
