# Freqtrade Control Panel (Flask)

Ce projet fournit une interface web légère (Flask) permettant de piloter
**Freqtrade** (téléchargement des données, backtests, hyperopt, gestion
des stratégies et push Git).\
Il simplifie les tâches récurrentes via une interface conviviale avec
suivi en direct (SSE).

------------------------------------------------------------------------

## 🚀 Utilité

-   Lancer des **backtests** et des **hyperopt** sans ligne de commande.
-   Appliquer facilement un fichier `.json` optimisé à une stratégie.
-   Télécharger les données historiques pour plusieurs timeframes (`3m`,
    `1h`, `1d`).
-   Gestion intégrée de **Git** (add/commit/push automatique).
-   Logs détaillés et accessibles depuis l'interface.

------------------------------------------------------------------------

## ⚙️ Installation

1.  Cloner votre dépôt (ou placer ce projet dans votre répertoire
    Freqtrade) :

    ``` bash
    git clone https://github.com/votre-utilisateur/votre-repo.git
    cd votre-repo
    ```

2.  Créer un environnement virtuel et installer les dépendances :

    ``` bash
    python -m venv .venv
    .venv\Scripts\activate     # sous Windows
    # source .venv/bin/activate  # sous Linux/Mac
    pip install flask
    ```

3.  Vérifier que **Freqtrade** est bien installé dans le projet (au
    besoin) :

    ``` bash
    pip install freqtrade
    ```

4.  (Optionnel) Créez un fichier `git_path.txt` listant vos dépôts Git à
    piloter :

    ``` txt
    # Exemple de contenu :
    C:/Users/Vous/Documents/freqtrade-strategies
    C:/Users/Vous/Documents/freqtrade-config
    ```

------------------------------------------------------------------------

## 🖥️ Utilisation

1.  Lancer l'application Flask :

    ``` bash
    .venv\Scripts\python.exe app.py
    ```

    Par défaut, le serveur démarre sur `http://127.0.0.1:5000`.

2.  Depuis votre navigateur, vous pourrez :

    -   Sélectionner une stratégie et une période.\
    -   Lancer un **Download data**, **Backtest**, **Backtest BEAR** ou
        un **Hyperopt**.\
    -   Appliquer un fichier `.json` optimisé via **Apply Strategy**.\
    -   Faire un **Git Push** automatique du répertoire choisi.\
    -   Consulter les **logs** en direct.

------------------------------------------------------------------------

## 📂 Structure attendue

    .
    ├── app.py               # Interface Flask
    ├── git_path.txt         # Liste des chemins Git à gérer (optionnel)
    ├── user_data/
    │   └── strategies/      # Vos stratégies .py et fichiers .json
    └── log_app/             # Logs générés automatiquement

------------------------------------------------------------------------

## ✅ Notes

-   Pendant un **Hyperopt**, les boutons **Backtest** et **Backtest
    BEAR** sont désactivés, et inversement.\
-   Les listes de stratégies, `.json` et dépôts Git sont mises à jour
    automatiquement à la fin de chaque action.\
-   Les logs sont sauvegardés dans `log_app/` et consultables via
    l'onglet **Logs**.
