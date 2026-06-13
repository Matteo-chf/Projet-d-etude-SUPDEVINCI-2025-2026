from urllib.parse import urlparse
from mongo_service import MongoService

# --- Listes de sources à ajuster selon vos critères ---

TRUSTED_DOMAINS = {
    # Agences de presse internationales
    "reuters.com", "apnews.com", "afp.com",
    # Presse anglophone
    "bbc.com", "bbc.co.uk", "theguardian.com", "nytimes.com",
    "washingtonpost.com", "npr.org", "pbs.org",
    # Presse française
    "lemonde.fr", "lefigaro.fr", "liberation.fr", "leparisien.fr",
    "francetvinfo.fr", "france24.com", "rfi.fr", "20minutes.fr",
    "lexpress.fr", "lepoint.fr",
    # Fact-checkers
    "factcheck.org", "snopes.com", "politifact.com",
    "lesdecodeurs.fr", "checknews.fr", "liberation.fr",
    "verafiles.org", "fullfact.org",
    # Institutions scientifiques / gouvernementales
    "who.int", "cdc.gov", "europa.eu", "gouvernement.fr",
    "nature.com", "science.org", "pubmed.ncbi.nlm.nih.gov",
}

UNTRUSTED_DOMAINS = {
    # Sources identifiées comme vecteurs de désinformation
    "infowars.com", "naturalnews.com", "thegatewaypundit.com",
    "breitbart.com", "rt.com", "sputniknews.com", "tass.com",
    "beforeitsnews.com", "worldnewsdailyreport.com",
    "yournewswire.com", "newspunch.com",
}


def extract_url(doc: dict) -> str | None:
    """
    Extrait l'URL externe d'un document, quel que soit son format.
    Format 1 (script 4 bootstrap) : doc.embed.external.uri
    Format 2 (script 3 timeline)  : doc.data.feed[0].post.embed.external.uri
    """
    # Format direct (script 4)
    embed = doc.get("embed") or {}
    uri = embed.get("external", {}).get("uri")
    if uri:
        return uri

    # Format data.feed (script 3)
    feed = doc.get("data", {}).get("feed", [])
    if isinstance(feed, list) and feed:
        post = feed[0].get("post", {})
        embed2 = post.get("embed") or {}
        uri = embed2.get("external", {}).get("uri")
        if uri:
            return uri

    return None


def get_domain(url: str) -> str:
    """Extrait le domaine racine d'une URL (ex: sub.bbc.co.uk → bbc.co.uk)."""
    try:
        hostname = urlparse(url).hostname or ""
        # Retirer www.
        parts = hostname.lstrip("www.").split(".")
        # Garder les 2 derniers segments (ou 3 pour .co.uk etc.)
        if len(parts) >= 3 and parts[-2] in ("co", "com", "org", "gov", "net"):
            return ".".join(parts[-3:])
        return ".".join(parts[-2:]) if len(parts) >= 2 else hostname
    except Exception:
        return ""


def label_document(doc: dict) -> str:
    url = extract_url(doc)
    if not url:
        return "unknown"
    domain = get_domain(url)
    if domain in TRUSTED_DOMAINS:
        return "reliable"
    if domain in UNTRUSTED_DOMAINS:
        return "unreliable"
    return "unknown"


def run():
    mongo = MongoService()
    collection = mongo.db.timeline

    total = collection.count_documents({})
    print(f"Documents a traiter : {total}")

    stats = {"reliable": 0, "unreliable": 0, "unknown": 0}

    for doc in collection.find():
        label = label_document(doc)
        collection.update_one(
            {"_id": doc["_id"]},
            {"$set": {"source_label": label}}
        )
        stats[label] += 1

    print("\nResultats du labeling :")
    print(f"  reliable    : {stats['reliable']}")
    print(f"  unreliable  : {stats['unreliable']}")
    print(f"  unknown     : {stats['unknown']}")
    print(f"\nDocs utilisables pour l'entrainement : {stats['reliable'] + stats['unreliable']}")


if __name__ == "__main__":
    run()
