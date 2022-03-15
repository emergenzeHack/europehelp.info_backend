import json
import logging

import requests
import telegram
import tweepy
import yaml
from flask import Flask, request
from flask_cors import CORS
from geopy.geocoders import Nominatim

import credentials

geolocator = Nominatim(user_agent="europehelp.info")


bot = telegram.Bot(token=credentials.telegram_api_token)

client = tweepy.Client(
    consumer_key=credentials.consumer_key,
    consumer_secret=credentials.consumer_secret,
    access_token=credentials.access_token,
    access_token_secret=credentials.access_token_secret,
    bearer_token=credentials.bearer_token,
)


with open("italy_geo.json") as f:
    italy_geo = json.load(f)

with open("comuni.json") as f:
    comuni = json.load(f)

comuni = sorted(comuni, key=lambda k: k["popolazione"], reverse=True)

app = Flask(__name__)

cors = CORS(app)


# Authentication for user filing issue (must have read/write access to
# repository to add issue to)
USERNAME = credentials.user
PASSWORD = credentials.password

# The repository to add this issue to
REPO_OWNER = "emergenzeHack"
REPO_NAME = "europehelp.info_segnalazioni"

repo_names = {"en": "europehelp.info_segnalazioni"}


@app.route("/")
def paynoattention():
    app.logger.info("404")
    return "Pay no attention to that man behind the curtain!", 404


@app.route("/webhook", methods=["POST"])
def webhook():
    app.logger.info("request headers {}".format(request.headers))
    app.logger.info("request JSON {}".format(request.json))

    if request.json["action"] == "labeled":

        if request.json["label"]["name"] == "telegram-channel":
            msg = f"{request.json['issue']['title']} - https://ukrainehelp.emergenzehack.info/issues/{request.json['issue']['number']}/ "
            bot.send_message(text=msg, chat_id=-1001568943771)
        elif request.json["label"]["name"] == "tweet":
            msg = f"{request.json['issue']['title']} https://ukrainehelp.emergenzehack.info/issues/{request.json['issue']['number']}/ \n#UkraineHelpIt #UkraineWar #Ucraina"
            client.create_tweet(text=msg)
    else:
        print("ignoring payload..")

    return "OK", 200


@app.route("/report", methods=["POST"])
def report():
    app.logger.info("request headers {}".format(request.headers))
    app.logger.info("request JSON {}".format(request.json))
    process_report(request.json, request.headers)
    return "OK", 200


def process_report(request, headers_pre, additional_labels=[], issue_title=None):
    payload = request["data"]
    for k in payload.keys():
        try:
            payload[k] = payload[k].strip()
        except Exception as e:
            print(e)
            pass

    # Key names to lowercase
    # not sure why this is needed
    headers = {k.lower(): v for k, v in headers_pre.items()}
    app.logger.info("Processing %s with headers %s .." % (payload, headers))

    # Create an authenticated session to create the issue
    session = requests.Session()
    session.auth = (USERNAME, PASSWORD)

    labels = []
    # payload = request.json

    # Rimuovi nome gruppo dal nome delle chiavi
    # e.g. datibancari/IBAN -> datibancari
    for key_name in list(payload):
        if "datibancari/" in key_name:
            new_key_name = key_name.replace("datibancari/", "")
            payload[new_key_name] = payload[key_name]
            payload.pop(key_name)

    if "label" in list(payload):
        label = payload["label"]
    else:
        label = "form_raw"

    # If country is not specified, IT is default
    if "country" in list(headers):
        country = headers["country"]
    else:
        country = "en"

    location = False
    location_geo = False
    comment_body = None

    if issue_title is None:
        # Prepare the issue title
        meaningful_fields = {
            "it": ["Titolo", "Cosa", "Testo", "Descrizione"],
            "pt": ["Nome", "Finalidade"],
            "gr": [],
            "en": ["title", "what", "description"],
        }

        for field in meaningful_fields[country]:
            if field in list(payload):
                if len(payload[field]) > 0:
                    issue_title = payload[field][0:100]
                    break

        if "Chi" in list(payload) and label == "Raccolte fondi":
            issue_title = "Raccolta fondi %s" % (payload["Chi"])

        if not issue_title:
            issue_title = label

    if country == "it":
        # Assegna le label in base alle selezioni sul form "Iniziative"
        if label == "iniziativa":
            if "Natura" in list(payload):
                if payload["Natura"] == "culturale-ricr":
                    label = "Attivita culturali e ricreative"
                elif payload["Natura"] == "solidale":
                    label = "Servizi e iniziative solidali "
                    if "Tipo_di_soggetto" in list(payload):
                        if payload["Tipo_di_soggetto"] == "privato":
                            label += "private"
                        else:
                            label += "pubbliche"
                elif payload["Natura"] == "didattica":
                    label = "Didattica a distanza e-learning"
                elif payload["Natura"] == "sostegno-lavor":
                    label = "Sostegno lavoro e imprese"

        # Se trovi riferimenti a psicologi o psicoterapeuti,
        #  aggiungi la label "Supporto Psicologico"
        if "Titolo" in list(payload):
            if (
                "psicolog" in payload["Titolo"].lower()
                or "psicoter" in payload["Titolo"].lower()
            ):
                labels.append("Supporto Psicologico")
            else:
                if "Descrizione" in list(payload):
                    if (
                        "psicolog" in payload["Descrizione"].lower()
                        or "psicoter" in payload["Descrizione"].lower()
                    ):
                        labels.append("Supporto Psicologico")

        # Suggerisci una posizione
        if "Indirizzo" not in list(payload) and "Posizione" not in list(payload):
            location = False
            if "Titolo" in list(payload):
                location = extract_location(payload["Titolo"])
            elif "Da_chi_offerta" in list(payload):
                location = extract_location(payload["Da_chi_offerta"])
            elif "Cosa" in list(payload) and not location:
                location = extract_location(payload["Cosa"])
            elif "Testo" in list(payload) and not location:
                location = extract_location(payload["Testo"])
            elif "Descrizione" in list(payload) and not location:
                location = extract_location(payload["Descrizione"])

        if "location" in payload and "Posizione" not in payload:
            location_geo = None
            tries = 0
            while location_geo is None:
                tries += 1
                if tries < 10:
                    try:
                        print("Getting coordinates. (%s)" % (tries))
                        location_input = payload["location"]
                        location_geo = geolocator.geocode(payload["location"])
                    except Exception:
                        pass
                else:
                    location_geo = 0
            if location_geo != 0:
                payload["Posizione"] = (
                    str(location_geo.latitude) + " " + str(location_geo.longitude)
                )
                payload.pop("location")

        if location_geo:
            coords = payload["Posizione"].split(" ")
            comment_message = (
                "Sembra che questa segnalazione non sia geolocalizzata. Ho automaticamente aggiunto %s (%s) come coordinate. Per favore, controlla <a href='https://nominatim.openstreetmap.org/search.php?q=%s+%s&polygon_geojson=1&viewbox='>qui</a> se sono corrette. In caso positivo, rimuovi pure la label 'Posizione da verificare' da questa Issue, altrimenti, procedi a correggere o rimuovere la posizione come spiegato <a href='https://github.com/emergenzeHack/covid19italia/wiki/Lavorare-sulle-segnalazioni#aggiungere-geolocalizzazione'>qui</a>."
                % (payload["Posizione"], location_input, coords[0], coords[1])
            )
            comment_body = {"body": comment_message}
            labels.append("Posizione da verificare")

        # Commenta con il suggerimento
        if location:
            # payload["Indirizzo"] = location[0]
            coords = location[0].split(" ")
            comment_message = (
                "Sembra che questa segnalazione non sia geolocalizzata. Ho automaticamente aggiunto %s (%s) come coordinate. Per favore, controlla <a href='https://nominatim.openstreetmap.org/search.php?q=%s+%s&polygon_geojson=1&viewbox='>qui</a> se sono corrette. In caso positivo, rimuovi pure la label 'Posizione da verificare' da questa Issue, altrimenti, procedi a correggere o rimuovere la posizione come spiegato <a href='https://github.com/emergenzeHack/covid19italia/wiki/Lavorare-sulle-segnalazioni#aggiungere-geolocalizzazione'>qui</a>."
                % (location[0], location[1], coords[0], coords[1])
            )
            comment_body = {"body": comment_message}
            labels.append("Posizione da verificare")

    if "location" in payload:
        location = payload["location"]
        address = location["address"]
        if "lat" in address:
            lat = address["lat"]
            if "lon" in address:
                lon = address["lon"]
                payload["Posizione"] = str(lat) + " " + str(lon)

    positionFound = None
    positionLabels = ["Posizione", "location", "Indirizzo"]

    for labelname in positionLabels:
        # Aggiungi label posizione mancante
        if labelname in list(payload):
            positionFound = True

    if not positionFound and not location and not location_geo:
        if country == "it":
            labels.append("Posizione mancante")
        else:
            labels.append("Missing position")

    # Aggiungi sempre la label "form" per le issue provenienti da questo script
    # labels.append("form")
    # Aggiungi le label preparate
    labels.append(label)

    for label in additional_labels:
        labels.append(label)

    # Rimuovi metavalori
    stripped_payload = strip_meta(payload)

    blacklist = ["promozioniltaliane.com", "vuedc.info"]

    # FIXME this has to be restored in some other way
    # for word in blacklist:
    #    for field in list(payload):
    #        if word in payload[field]:
    #            labels.append("spam")

    # Prepara il payload in YAML
    yaml_payload = (
        "<pre><yamldata>\n"
        + yaml.dump(stripped_payload, allow_unicode=True, sort_keys=False)
        + "</yamldata></pre>"
    )

    # Apri issue su GitHub
    comment_url = open_github_issue(
        session, title=issue_title, body=yaml_payload, labels=labels, country=country
    )

    if comment_body:
        add_comment(session, url=comment_url, body=comment_body)

    return


def strip_meta(payload):
    excludelist = [
        "end",
        "start",
        "formhub/uuid",
        "meta/instanceID",
        "meta/deprecatedID",
        "Informativa",
    ]
    # Rimuovi tutti i campi meta che iniziano con _
    for k in list(payload):
        if k.startswith("_"):
            payload.pop(k)
        # Rimuovi anche le chiavi specificate nella lista
        elif k in excludelist:
            payload.pop(k)
    return payload


def extract_location(text):
    for comune in comuni[0:150]:
        if len(comune["nome"]) > 3 and "%s" % (comune["nome"].lower()) in text.lower():
            for com_geo in italy_geo:
                if com_geo["comune"].lower() == comune["nome"].lower():
                    print("Trovato riferimento a comune", comune["nome"])
                    location = com_geo["lat"] + " " + com_geo["lng"]
                    print("Aggiungo", location)
                    return [location, comune["nome"]]

    return False


def add_comment(session, url, body):
    r = session.post(url, json.dumps(body))
    if r.status_code == 201:
        print("Successfully created Comment on Issue")

    else:
        print("Could not create Comment", title)
        print("Response:", r.content)


def open_github_issue(
    session, title, body=None, assignee=None, milestone=None, labels=[], country="it"
):
    """Create an issue on github.com using the given parameters."""

    # Create our issue
    issue = {
        "title": title,
        "body": body,
        "assignee": assignee,
        "milestone": milestone,
        "labels": labels,
    }

    # Our url to create issues via POST
    url = "https://api.github.com/repos/%s/%s/issues" % (
        REPO_OWNER,
        repo_names[country],
    )

    # Add the issue to our repository
    r = session.post(url, json.dumps(issue))

    if r.status_code == 201:
        print("Successfully created Issue", title)
        response = r.json()
        return response["comments_url"]

    else:
        print("Could not create Issue", title)
        print("Response:", r.content)


print(__name__)
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=3010, debug=True)
else:
    print("o")
    gunicorn_logger = logging.getLogger("gunicorn.error")
    app.logger.handlers = gunicorn_logger.handlers
    app.logger.setLevel(gunicorn_logger.level)
    app.logger.info("Using gunicorn logger")
