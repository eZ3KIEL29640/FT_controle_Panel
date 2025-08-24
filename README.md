# 📊 Freqtrade Control Panel (Flask UI)

Une interface web légère en **Flask** pour piloter **Freqtrade** sans ligne de commande.  
Elle permet de gérer **les stratégies, les backtests, l’hyperopt, les téléchargements de données et le push Git** via un simple navigateur.

<img width="1228" height="1178" alt="image" src="https://github.com/user-attachments/assets/5f0f3860-686e-4ea0-a142-3ec6dc3ea705" />



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
│	│	├── config_exchange.json
│	│	├── config_secrets.json
│	│	├── config_strategy.json
│	│	├── ...
│   └── strategies/          # Stratégies et résultats Hyperopt (.py / .json)
│
├── log_app/                 # Logs générés par l’UI
└── git_path.txt             # Liste des dépôts Git à utiliser pour “PUSH”
```
- Créer des liens symboliques :  
  `entre votre GIT Configs et user_data/configs`.
  
  `entre votre GIT strategies et user_data/strategies`. 

- Les paires utilisées pour le download sont lues depuis :  
  `user_data/configs/config_exchange.json → pair_whitelist`.  

## 📂 Fichiers

- config_base.json
```
{
  "bot_name": "eZ3KIEL",
  "$schema": "https://schema.freqtrade.io/schema.json",

  "stake_currency": "USDC",
  "timeframe": "3m",
  "trading_mode": "spot",

  "pairlists": [
    { "method": "StaticPairList" }
  ],

  "add_config_files": [
    "configs/config_strategy.json",
    "configs/config_freqai.json",
    "configs/config_exchange.json",
    "configs/config_secrets.json"
  ]
}
```

## 📂 Strategie

- Doit contenir ce morceau de code sous la class :

```
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        json_path = Path(__file__).resolve().parent / "eZ3_scalp3m.json"
        if json_path.exists():
            with open(json_path, "r", encoding="utf-8") as f:
                self.cfg = json.load(f)
        else:
            self.cfg = {}
```

## 📂 BOT Freqtrade

- Bash check.sh :

```
#!/bin/sh

set -e

FT_STRAT=/home/debian/STRATS/FT_strat_live
FT_CONFIG=/home/debian/CONFIG/FT_config_live
FREQTRADE_HOME=/home/debian/freqtrade

cd $FT_STRAT
changed=0
git pull | grep -q 'Already up to date.' && changed=1
if [ $changed = 0 ]; then
    git pull
        rm -f $FREQTRADE_HOME/user_data/strategies/.py
        cp -f $FT_STRAT/.py $FREQTRADE_HOME/user_data/strategies/
        sudo systemctl restart freqtrade_spot.service
        echo "updating NFO Strategy"

else
    echo "Up-to-date"
fi

cd $FT_CONFIG
changed=0
git pull | grep -q 'Already up to date.' && changed=1
if [ $changed = 0 ]; then
    git pull
        rm -f $FREQTRADE_HOME/user_data/config/*
        cp -f  $FT_CONFIG/configs/* $FREQTRADE_HOME/user_data/configs/
        cp -rf $FT_CONFIG/* $FREQTRADE_HOME/user_data/
        sudo systemctl restart freqtrade_spot.service
        echo "updating NFO Strategy"

else
    echo "Up-to-date"
fi
```

- Crontab :

```
* * * * * sudo /home/debian/check.sh > /home/debian/check.log
```

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

3. **Configurer** vos fichiers `user_data/config_base.json` et `user_data/configs/config_exchange.json ...`  
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
  👉 [Pay with BTC](bitcoin:bc1qukc8c3qhv04gxj3u9fawdtexx2nf0acmd8pspq?amount=0.0000305&label=Pay%20me%20a%20coffee)  
  - Device: **BTC**  
  - Network: **Native SegWit (bech32)**  
  - Address: `bc1qukc8c3qhv04gxj3u9fawdtexx2nf0acmd8pspq`  

---

- **Ethereum (ETH)** : ~0.00074 ETH  
  👉 [Pay with ETH](ethereum:0x2e2c095f7cc235eb485cca0dbe2b0cb9d923761a?amount=0.00074&label=Pay%20me%20a%20coffee)  
  - Device: **ETH**  
  - Network: **ERC20**  
  - Address: `0x2e2c095f7cc235eb485cca0dbe2b0cb9d923761a`  

🙏 Merci beaucoup !

---
