# Service de recherche web sur sources fiables
#
# Stratégie : recherche DuckDuckGo sans filtre site: (plus fiable),
# puis on garde uniquement les résultats provenant de domaines de confiance.
# Les résultats datés (recherche "news") sont triés du plus récent au plus ancien
# et priorisés sur les résultats non datés (recherche "text", utilisée en complément).

from datetime import datetime, timezone
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


def _parse_date(date_str: str):
    """Parse une date ISO renvoyée par ddgs. None si absente/illisible."""
    if not date_str:
        return None
    try:
        return datetime.fromisoformat(date_str)
    except ValueError:
        return None


def search_web(query: str, max_results: int = MAX_TRUSTED) -> tuple[list[dict], str | None]:
    """
    Recherche des articles sur le sujet, sources fiables uniquement.
    Priorise les articles les plus récents (recherche "news", datée),
    puis complète avec la recherche texte classique si besoin.
    Retourne (résultats_fiables, message_erreur_ou_None).
    Retry automatique 3 fois avec délai croissant si DuckDuckGo rate-limite.
    """
    import time

    last_error = None
    for attempt in range(3):
        try:
            trusted   = []
            seen_urls = set()

            # 1. Recherche "news" : résultats datés → tri du plus récent au plus ancien
            try:
                raw_news = list(DDGS().news(query, max_results=RAW_RESULTS))
            except Exception:
                raw_news = []

            dated = []
            for r in raw_news:
                url    = r.get("url", "")
                domain = get_domain(url)
                if domain in TRUSTED_DOMAINS and url not in seen_urls:
                    dated.append({
                        "title":         r.get("title", ""),
                        "url":           url,
                        "snippet":       r.get("body", ""),
                        "source_domain": domain,
                        "date":          r.get("date", ""),
                    })
            dated.sort(key=lambda a: _parse_date(a["date"]) or datetime.min.replace(tzinfo=timezone.utc), reverse=True)

            for a in dated:
                if len(trusted) >= max_results:
                    break
                trusted.append(a)
                seen_urls.add(a["url"])

            # 2. Complément non daté (recherche texte classique) si pas assez de résultats
            if len(trusted) < max_results:
                raw_text = list(DDGS().text(query, max_results=RAW_RESULTS))
                for r in raw_text:
                    if len(trusted) >= max_results:
                        break
                    url    = r.get("href", "")
                    domain = get_domain(url)
                    if domain in TRUSTED_DOMAINS and url not in seen_urls:
                        trusted.append({
                            "title":         r.get("title", ""),
                            "url":           url,
                            "snippet":       r.get("body", ""),
                            "source_domain": domain,
                            "date":          "",
                        })
                        seen_urls.add(url)

            return trusted, None

        except Exception as e:
            last_error = e
            wait = 2 ** attempt  # 1s, 2s, 4s
            print(f"  [Web Search] Tentative {attempt + 1}/3 échouée : {e} — attente {wait}s")
            time.sleep(wait)

    msg = f"Recherche web indisponible (DuckDuckGo rate-limit ou réseau) : {last_error}"
    print(f"  [Web Search] Abandon après 3 tentatives : {last_error}")
    return [], msg


def search_wikipedia(query: str) -> dict | None:
    """
    Recherche l'article Wikipedia le plus pertinent pour le sujet.
    Essaie le Wikipedia francophone en premier (les news analysées sont en français),
    puis se replie sur l'anglophone si rien n'est trouvé.
    Retourne {title, url, snippet} ou None si rien de pertinent n'est trouvé.
    """
    results = []
    for region in ("fr-fr", "us-en"):
        try:
            results = list(DDGS().text(query, backend="wikipedia", region=region, max_results=1))
        except Exception as e:
            print(f"  [Web Search] Wikipedia ({region}) indisponible : {e}")
            results = []
        if results:
            break

    if not results:
        return None

    r = results[0]
    return {
        "title":   r.get("title", ""),
        "url":     r.get("href", ""),
        "snippet": (r.get("body", "") or "")[:300],
    }