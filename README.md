# covid19italia.help - Modulistica

## frontend

I [form](https://www.covid19italia.info/segnala/) (in XLSform) vengono mantenuti e serviti su https://kobo.humanitarianresponse.info

Le POST provenienti da quei form puntano al backend implementato qui.

## backend

`server.py` si occupa di ricevere le risposte ai form ed inviarle come GitHub Issues al repository [covid19italia_segnalazioni](https://github.com/emergenzeHack/covid19italia_segnalazioni/)

Prerequisiti

```bash
apt install python3
```

Avvio

```bash
python3 -m venv env
source env/bin/activate
pip install -r requirements.txt
```

## utils

Gli script `import*.py` processano file CSV e ne preparano issue github da aprire sul repository [covid19italia_segnalazioni](https://github.com/emergenzeHack/covid19italia_segnalazioni/). Vedere sorgenti collegate per i CSV originali e altre informazioni.
