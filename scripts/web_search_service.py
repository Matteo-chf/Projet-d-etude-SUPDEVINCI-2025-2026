# Service de recherche web sur sources fiables
#
# Stratégie : recherche DuckDuckGo sans filtre site: (plus fiable),
# puis on garde uniquement les résultats provenant de domaines de confiance.

from urllib.parse import urlparse
from ddgs import DDGS  # pip install ddgs

# Liste large de domaines fiables pour capter un maximum de résultats DuckDuckGo
TRUSTED_DOMAINS = {
    # Agences de presse
    "reuters.com", "apnews.com", "afp.com", "bloomberg.com",
    # Presse anglophone
    "bbc.com", "bbc.co.uk", "theguardian.com", "nytimes.com",
    "washingtonpost.com", "ft.com", "economist.com", "politico.com",
    "nbcnews.com", "cbsnews.com", "npr.org", "independent.co.uk",
    # Presse française nationale
    "lemonde.fr", "lefigaro.fr", "liberation.fr", "leparisien.fr",
    "francetvinfo.fr", "france24.com", "rfi.fr", "20minutes.fr",
    "lexpress.fr", "lepoint.fr", "nouvelobs.com", "mediapart.fr",
    "lesechos.fr", "bfmtv.com", "tf1info.fr", "lci.fr",
    "la-croix.com", "latribune.fr", "challenges.fr",
    # Presse française régionale
    "ouest-france.fr", "sudouest.fr", "lavoixdunord.fr",
    # Presse européenne et internationale
    "euronews.com", "spiegel.de", "elpais.com", "corriere.it",
    "tagesschau.de", "rtbf.be", "lesoir.be", "rts.ch", "letemps.ch",
    "lapresse.ca", "ledevoir.com", "radio-canada.ca",
    # Institutions
    "who.int", "un.org", "europa.eu", "gouvernement.fr",
    "elysee.fr", "assemblee-nationale.fr", "nasa.gov", "nih.gov",
    # Fact-checkers
    "factcheck.org", "snopes.com", "lesdecodeurs.fr", "checknews.fr",
}

# Nombre de résultats bruts à récupérer avant filtrage
RAW_RESULTS = 20
MAX_TRUSTED = 3


def get_domain(url: str) -> str:
    """Extrait le domaine racine d'une URL. Utilise removeprefix pour éviter le bug lstrip."""
    try:
        hostname = urlparse(url).hostname or ""
        # removeprefix retire exactement "www." sans toucher au reste du hostname
        hostname = hostname.removeprefix("www.")
        parts    = hostname.split(".")
        # Gère les TLD composés : .co.uk, .com.br, .org.au…
        if len(parts) >= 3 and parts[-2] in ("co", "com", "org", "gov", "net"):
            return ".".join(parts[-3:])
        return ".".join(parts[-2:]) if len(parts) >= 2 else hostname
    except Exception:
        return ""


def search_web(query: str, max_results: int = MAX_TRUSTED) -> list[dict]:
    """
    Recherche des articles récents sur le sujet.
    Retourne uniquement les résultats issus de sources fiables (filtrés par domaine).
    """
    try:
        raw = DDGS().text(query, max_results=RAW_RESULTS)
    except Exception as e:
        print(f"  [Web Search] Erreur : {e}")
        return []

    trusted = []
    for r in raw:
        url    = r.get("href", "")
        domain = get_domain(url)
        if domain in TRUSTED_DOMAINS:
            trusted.append({
                "title":         r.get("title", ""),
                "url":           url,
                "snippet":       r.get("body", ""),
                "source_domain": domain,
            })
        if len(trusted) >= max_results:
            break

    return trusted