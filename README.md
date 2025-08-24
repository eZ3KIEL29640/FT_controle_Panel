# 📊 Freqtrade Control Panel (Flask UI)

Une interface web légère en **Flask** pour piloter **Freqtrade** sans ligne de commande.  
Elle permet de gérer **les stratégies, les backtests, l’hyperopt, les téléchargements de données et le push Git** via un simple navigateur.

---

## 🚀 Utilité

- Démarrer rapidement un **download de données** (multi-timeframes, progression avec barre).  
- Lancer des **backtests** ou un **backtest BEAR** directement depuis l’UI.  
- Exécuter un **hyperopt** avec gestion des `spaces` (all / default / personnalisés).  
- **Appliquer** un JSON hyperopté à une stratégie donnée.  
- **Pousser sur Git** vos modifications (add/commit/push).  
- Visualiser et télécharger les **logs générés**.  

---

## 📂 Répertoires

```
project_root/
│
├── app.py                  # Application Flask (UI principale)
├── user_data/
│   ├── config_base.json     # Config principale utilisée par toutes les actions
│   ├── configs/             # Configs additionnelles (dont config_exchange.json)
│   └── strategies/          # Stratégies et résultats Hyperopt (.py / .json)
│
├── log_app/                 # Logs générés par l’UI
└── git_path.txt             # Liste des dépôts Git à utiliser pour “PUSH”
```

- Les paires utilisées pour le download sont lues depuis :  
  `user_data/configs/config_exchange.json → pair_whitelist`.  

---

## ⚙️ Installation

1. **Cloner** votre repo contenant Freqtrade et cette UI.
   ```bash
   git clone https://github.com/votre-repo/freqtrade-ui.git
   cd freqtrade-ui
   ```

2. **Créer un venv** Python et installer Flask :
   ```bash
   python -m venv .venv
   .\.venv\Scripts\activate    # sous Windows
   # ou source .venv/bin/activate sous Linux/Mac

   pip install flask
   ```

3. **Configurer** vos fichiers `user_data/config_base.json` et `user_data/configs/config_exchange.json`  
   (ajoutez vos `pair_whitelist`, clés API, etc.).

---

## ▶️ Utilisation

1. Démarrer l’UI :
   ```bash
   .venv\Scripts\python.exe app.py
   ```
   (par défaut sur [http://127.0.0.1:5000](http://127.0.0.1:5000))

2. Ouvrir le navigateur : vous aurez accès à :
   - **Strategy** : choix du script, dates, compteur `pair_whitelist`.  
   - **Download** : choix des timeframes, option `--erase`, barre de progression.  
   - **Backtest** / **Backtest BEAR** : exécution avec résultats affichés.  
   - **Hyperopt** : epochs + choix des spaces avec contraintes intelligentes.  
   - **Apply Strategy Hyperopt** : appliquer un `.json` optimisé.  
   - **Git PUSH** : commit + push automatique.  
   - **Logs** : consultation en direct.  

3. Tous les résultats et erreurs apparaissent dans les panneaux de sortie.  
   Les logs sont également sauvegardés dans `log_app/`.

---

## ☕ Pay me a coffee

Si ce projet vous aide, vous pouvez m’offrir un café (~3,50 USD) en crypto :  

- **Bitcoin (BTC)** : ~0.000030 BTC  
  👉 [Pay with BTC](bitcoin:0x2e2c095f7cc235eb485cca0dbe2b0cb9d923761a?amount=0.0000305&label=Pay%20me%20a%20coffee)  

- **Ethereum (ETH)** : ~0.00074 ETH  
  👉 [Pay with ETH](ethereum:0x2e2c095f7cc235eb485cca0dbe2b0cb9d923761a?value=740000000000000&label=Pay%20me%20a%20coffee)  

🙏 Merci beaucoup !

---
