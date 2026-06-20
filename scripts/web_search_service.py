# Service de recherche web sur sources fiables
#
# Utilise DuckDuckGo Search (gratuit, sans clé API) pour trouver des articles
# récents sur le sujet analysé, filtrés sur les domaines de confiance.
# Complète le RAG MongoDB avec des résultats en temps réel depuis le web.

from urllib.parse import urlparse
from duckduckgo_search import DDGS  # pip install duckduckgo-search

# Sous-ensemble de domaines fiables optimisé pour la recherche DuckDuckGo
# (on limite à ~15 domaines pour que la requête site: reste lisible)
SEARCH_DOMAINS = [
    # Agences internationales
    "reuters.com", "apnews.com", "afp.com", "bloomberg.com",
    # Presse anglophone
    "bbc.com", "theguardian.com", "nytimes.com", "ft.com",
    # Presse française
    "lemonde.fr", "lefigaro.fr", "francetvinfo.fr", "france24.com",
    "liberation.fr", "lesechos.fr", "rfi.fr",
    # Institutions
    "who.int", "un.org",
]


def get_domain(url: str) -> str:
    """Extrait le domaine racine d'une URL."""
    try:
        hostname = urlparse(url).hostname or ""
        parts = hostname.lstrip("www.").split(".")
        if len(parts) >= 3 and parts[-2] in ("co", "com", "org", "gov", "net"):
            return ".".join(parts[-3:])
        return ".".join(parts[-2:]) if len(parts) >= 2 else hostname
    except Exception:
        return ""


def search_web(query: str, max_results: int = 5) -> list[dict]:
    """
    Recherche des articles récents sur le sujet depuis des sources fiables.
    Retourne une liste de dicts : title, url, snippet, source_domain.
    """
    # Filtre DuckDuckGo : site:reuters.com OR site:bbc.com OR ...
    site_filter = " OR ".join(f"site:{d}" for d in SEARCH_DOMAINS)
    full_query   = f"{query} ({site_filter})"

    try:
        results = DDGS().text(full_query, max_results=max_results)
    except Exception as e:
        print(f"  [Web Search] Erreur : {e}")
        return []

    articles = []
    for r in results:
        url    = r.get("href", "")
        domain = get_domain(url)
        articles.append({
            "title":         r.get("title", ""),
            "url":           url,
            "snippet":       r.get("body", ""),
            "source_domain": domain,
        })

    return articles