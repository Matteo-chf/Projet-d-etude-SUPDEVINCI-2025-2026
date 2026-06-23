from bluesky_api import bootstrap_from_keywords
from mongo_service import MongoService

# Mots-cles generiques d'actualite, pour constituer un corpus large de posts
GENERAL_KEYWORDS = [
    # Noms de médias tels qu'écrits dans les posts Bluesky
    "news", "breaking news", "reuters", "bbc news", "bloomberg", "apnews", "afp",
    "le monde", "le figaro", "libération", "france24", "francetvinfo",
    "rfi", "nouvel obs", "mediapart", "les echos", "bfmtv",
    "el pais", "der spiegel", "the guardian", "financial times",
    "press release", "headline", "exclusive",
    # Politique et société
    "election", "politics", "government", "democracy", "parliament",
    "president", "senate", "congress", "vote", "policy",
    "politique", "élection", "gouvernement", "parlement", "sénat",
    # Santé
    "health", "vaccine", "covid", "who", "medicine", "hospital",
    "pandemic", "outbreak", "treatment",
    "santé", "vaccin", "épidémie", "oms", "médicament",
    # Environnement
    "climate", "environment", "global warming", "wildfire", "drought",
    "renewable energy", "pollution",
    "climat", "environnement", "réchauffement", "énergie renouvelable",
    # Économie
    "economy", "inflation", "finance", "stock market", "unemployment",
    "interest rate", "recession",
    "économie", "banque centrale", "croissance", "bourse",
    # Science et technologie
    "science", "research", "study", "artificial intelligence",
    "recherche", "découverte", "intelligence artificielle",
    # Géopolitique
    "ukraine", "war", "conflict", "migration", "nato", "sanctions",
    "ceasefire", "diplomacy",
    "guerre", "conflit", "otan", "diplomatie",
    # Justice et société
    "justice", "human rights", "corruption",
    "droits humains", "tribunal",
]

# Domaines reconnus comme sources de desinformation (Media Bias/Fact Check,
# NewsGuard, EU vs Disinfo) : recherches par nom de domaine pour alimenter
# le label "unreliable".
UNRELIABLE_KEYWORDS = [
    "infowars.com", "naturalnews.com", "beforeitsnews.com",
    "worldnewsdailyreport.com", "yournewswire.com", "newspunch.com",
    "davidicke.com", "100percentfedup.com", "humansarefree.com",
    "rt.com", "sputniknews.com", "tass.com",
    "thegatewaypundit.com", "breitbart.com", "zerohedge.com",
    "theepochtimes.com", "oann.com", "veteranstoday.com",
    "lifesitenews.com", "globalresearch.ca",
]

KEYWORDS = GENERAL_KEYWORDS + UNRELIABLE_KEYWORDS

PAGES_PER_KEYWORD = 10
LIMIT_PER_PAGE = 100


if __name__ == "__main__":
    mongo = MongoService()

    estimated = len(KEYWORDS) * PAGES_PER_KEYWORD * LIMIT_PER_PAGE
    print(f"Lancement : {len(KEYWORDS)} mots-cles x {PAGES_PER_KEYWORD} pages x {LIMIT_PER_PAGE} posts = ~{estimated} posts max")
    print("(les doublons sont ignores automatiquement)\n")

    total = bootstrap_from_keywords(mongo, KEYWORDS, PAGES_PER_KEYWORD, LIMIT_PER_PAGE)
    print(f"Termine ! Total recu : ~{total} posts (sans compter les doublons ignores)")
