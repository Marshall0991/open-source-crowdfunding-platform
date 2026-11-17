# IMEI Guinée — Démonstrateur

Ce dépôt contient le démonstrateur **IMEI Guinée**, un registre national des téléphones déclarés volés
ou perdus. Il permet de déclarer un appareil, de faire valider la déclaration par la Police nationale
et de vérifier publiquement un IMEI.

Le code, l'installation, les comptes de démonstration et le scénario pas à pas se trouvent dans
[`imei-guinee/`](imei-guinee/README.md).

```bash
cd imei-guinee
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app
```
