# Étape 5 — Labellisation des posts par domaine source
#
# Deux signaux utilisés pour labéliser, par ordre de priorité :
#
#   1. HANDLE de l'auteur (signal fort)
#      Sur Bluesky, un handle comme "reuters.com" ou "nytimes.com" signifie que
#      Bluesky a vérifié que le compte contrôle ce domaine (vérification DNS).
#      C'est l'équivalent du badge bleu mais basé sur la propriété du domaine.
#
#   2. URL du lien partagé (signal secondaire)
#      Si le post contient un lien externe, on vérifie son domaine.
#      Ex : un post partageant "https://lemonde.fr/article/..." → reliable.
#
# Résultat stocké dans le champ "source_label" de chaque document MongoDB.

from urllib.parse import urlparse
from pymongo import UpdateOne
from mongo_service import MongoService

# Domaines de confiance : presse vérifiée, institutions, fact-checkers
TRUSTED_DOMAINS = {
    # Agences de presse internationales
    "reuters.com", "apnews.com", "afp.com", "bloomberg.com",
    "dpa-international.com", "efe.com", "ansa.it",

    # Presse anglophone — USA
    "bbc.com", "bbc.co.uk", "theguardian.com", "nytimes.com",
    "washingtonpost.com", "npr.org", "pbs.org", "cnn.com",
    "nbcnews.com", "cbsnews.com", "abcnews.go.com", "usatoday.com",
    "politico.com", "theatlantic.com", "newyorker.com",
    "economist.com", "ft.com", "time.com", "wired.com",
    "latimes.com", "bostonglobe.com", "chicagotribune.com",

    # Presse anglophone — UK / Irlande / Australie
    "independent.co.uk", "telegraph.co.uk", "thetimes.co.uk",
    "sky.com", "channel4.com", "irishtimes.com",
    "theage.com.au", "smh.com.au", "abc.net.au",

    # Presse française — nationale
    "lemonde.fr", "lefigaro.fr", "liberation.fr", "leparisien.fr",
    "francetvinfo.fr", "france24.com", "rfi.fr", "20minutes.fr",
    "lexpress.fr", "lepoint.fr", "nouvelobs.com", "mediapart.fr",
    "lesechos.fr", "latribune.fr", "la-croix.com", "humanite.fr",
    "challenges.fr", "lci.fr", "bfmtv.com", "tf1info.fr",
    "rtl.fr", "europe1.fr",

    # Presse française — régionale
    "ouest-france.fr", "sudouest.fr", "lavoixdunord.fr",
    "dna.fr", "lanouvellerepublique.fr", "leprogres.fr",
    "nicematin.com", "laprovence.com",

    # Presse francophone — Belgique / Suisse / Canada
    "rtbf.be", "lesoir.be", "lalibre.be", "levif.be",
    "rts.ch", "letemps.ch", "tdg.ch",
    "lapresse.ca", "ledevoir.com", "ici.radio-canada.ca",

    # Presse européenne
    "spiegel.de", "sueddeutsche.de", "faz.net", "zeit.de", "tagesschau.de",
    "elpais.com", "elmundo.es", "20minutos.es",
    "corriere.it", "repubblica.it", "lastampa.it",
    "nrc.nl", "nu.nl", "svt.se", "nrk.no", "yle.fi",
    "publico.pt", "observador.pt",

    # Fact-checkers reconnus
    "factcheck.org", "snopes.com", "politifact.com",
    "lesdecodeurs.fr", "checknews.fr", "verafiles.org",
    "fullfact.org", "africacheck.org", "correctiv.org",
    "maldita.es", "pagella-politica.it", "aapfactcheck.org",

    # Institutions internationales
    "who.int", "un.org", "worldbank.org", "imf.org",
    "europa.eu", "ecdc.europa.eu", "oecd.org",

    # Institutions gouvernementales
    "cdc.gov", "nih.gov", "nasa.gov", "gouvernement.fr",
    "elysee.fr", "assemblee-nationale.fr", "senat.fr",

    # Revues et institutions scientifiques
    "nature.com", "science.org", "pubmed.ncbi.nlm.nih.gov",
    "thelancet.com", "nejm.org", "bmj.com",
    "scientificamerican.com", "newscientist.com",
    "sciencedirect.com",
}

# Domaines non fiables : sites connus pour la désinformation
# (mêmes domaines que ceux ciblés par le bootstrap, cf. 4_bootstrap_data.py)
UNTRUSTED_DOMAINS = {
    "infowars.com", "naturalnews.com", "thegatewaypundit.com",
    "breitbart.com", "rt.com", "sputniknews.com", "tass.com",
    "beforeitsnews.com", "worldnewsdailyreport.com",
    "yournewswire.com", "newspunch.com",
    "davidicke.com", "100percentfedup.com", "humansarefree.com",
    "zerohedge.com", "theepochtimes.com", "oann.com",
    "veteranstoday.com", "lifesitenews.com", "globalresearch.ca",
}


def get_domain(url: str) -> str:
    """Extrait le domaine racine d'une URL (sans www, gère les TLD composés comme .co.uk)."""
    try:
        hostname = urlparse(url).hostname or ""
        parts = hostname.lstrip("www.").split(".")
        if len(parts) >= 3 and parts[-2] in ("co", "com", "org", "gov", "net"):
            return ".".join(parts[-3:])
        return ".".join(parts[-2:]) if len(parts) >= 2 else hostname
    except Exception:
        return ""


def extract_handle_domain(doc: dict) -> str:
    """
    Extrait le domaine du handle de l'auteur selon le format du document.
    Un handle custom (ex: 'nytimes.com') = compte vérifié par Bluesky via DNS.
    Un handle '.bsky.social' = compte non vérifié → on ignore.
    """
    handle = ""

    # Format searchPosts (script 4) : auteur à la racine du document
    if "author" in doc:
        handle = doc["author"].get("handle", "")

    # Format timeline (script 3) : auteur niché sous "post"
    elif "post" in doc:
        handle = doc["post"].get("author", {}).get("handle", "")

    # Ancien format : auteur dans data.feed
    elif "data" in doc:
        feed = doc["data"].get("feed", [])
        if feed:
            handle = feed[0].get("post", {}).get("author", {}).get("handle", "")

    # Ignore les handles Bluesky par défaut (.bsky.social) → non vérifiés
    if handle and not handle.endswith(".bsky.social"):
        return handle  # le handle custom EST le domaine (ex: "nytimes.com")

    return ""


def extract_url_domain(doc: dict) -> str:
    """Extrait le domaine de l'URL externe partagée dans le post (lien d'article)."""
    # Format searchPosts : embed à la racine
    embed = doc.get("embed") or {}
    uri = embed.get("external", {}).get("uri")
    if uri:
        return get_domain(uri)

    # Format timeline : embed niché sous "post"
    if "post" in doc:
        embed2 = doc["post"].get("embed") or {}
        uri = embed2.get("external", {}).get("uri")
        if uri:
            return get_domain(uri)

    # Ancien format : embed dans data.feed
    feed = doc.get("data", {}).get("feed", [])
    if isinstance(feed, list) and feed:
        embed3 = feed[0].get("post", {}).get("embed") or {}
        uri = embed3.get("external", {}).get("uri")
        if uri:
            return get_domain(uri)

    return ""


def label_document(doc: dict) -> tuple[str, str]:
    """
    Retourne (label, source) pour un document.
    - label  : 'reliable', 'unreliable' ou 'unknown'
    - source : 'handle' ou 'url' (indique quel signal a déclenché le label)

    Priorité : handle vérifié > URL partagée
    """
    # Signal 1 : handle de l'auteur (vérification Bluesky par DNS)
    handle_domain = extract_handle_domain(doc)
    if handle_domain:
        if handle_domain in TRUSTED_DOMAINS:
            return "reliable", "handle"
        if handle_domain in UNTRUSTED_DOMAINS:
            return "unreliable", "handle"

    # Signal 2 : domaine du lien partagé dans le post
    url_domain = extract_url_domain(doc)
    if url_domain:
        if url_domain in TRUSTED_DOMAINS:
            return "reliable", "url"
        if url_domain in UNTRUSTED_DOMAINS:
            return "unreliable", "url"

    return "unknown", "none"


def run():
    mongo = MongoService()
    collection = mongo.db.timeline

    total = collection.count_documents({})
    print(f"Documents a traiter : {total}\n")

    stats        = {"reliable": 0, "unreliable": 0, "unknown": 0}
    source_stats = {"handle": 0, "url": 0, "none": 0}

    BATCH_SIZE = 1000
    batch = []

    cursor = collection.find(batch_size=BATCH_SIZE)
    try:
        for doc in cursor:
            label, source = label_document(doc)
            batch.append(UpdateOne(
                {"_id": doc["_id"]},
                {"$set": {"source_label": label, "label_source": source}}
            ))
            stats[label]        += 1
            source_stats[source] += 1

            if len(batch) >= BATCH_SIZE:
                collection.bulk_write(batch, ordered=False)
                batch.clear()

        if batch:
            collection.bulk_write(batch, ordered=False)
    finally:
        cursor.close()

    print("Resultats du labeling :")
    print(f"  reliable    : {stats['reliable']}")
    print(f"  unreliable  : {stats['unreliable']}")
    print(f"  unknown     : {stats['unknown']}")
    print(f"\nSignal ayant déclenché le label :")
    print(f"  via handle vérifié Bluesky : {source_stats['handle']}")
    print(f"  via URL partagée           : {source_stats['url']}")
    print(f"  aucun signal               : {source_stats['none']}")
    print(f"\nDocs utilisables pour le RAG : {stats['reliable']}")


if __name__ == "__main__":
    run()
