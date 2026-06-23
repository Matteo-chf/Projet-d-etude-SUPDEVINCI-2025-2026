import os
import sys
import re
import html as html_lib
from concurrent.futures import ThreadPoolExecutor

import spacy
import streamlit as st

ROOT_DIR    = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS_DIR = os.path.join(ROOT_DIR, "scripts")
sys.path.insert(0, SCRIPTS_DIR)

from rag_service import RAGCredibilityService, LABEL_FR, LABEL_ICON
from web_search_service import search_wikipedia

# Tags spaCy considérés comme nom propre / nom commun
NOUN_POS = {"NOUN", "PROPN"}

# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Fact-Checker IA",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── CSS — Newspaper style, no page scroll ────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@700;900&family=IM+Fell+English&family=Libre+Baskerville:ital,wght@0,400;0,700;1,400&display=swap');

/* ═══ BASE PAPIER ═══ */
html, body {
    overflow: hidden !important;
    height: 100vh !important;
    background: #f8f4ea !important;
}
[data-testid="stAppViewContainer"] {
    background: #f8f4ea !important;
    overflow: hidden !important;
    height: 100vh !important;
}
[data-testid="stMain"] {
    background: #f8f4ea !important;
    overflow: hidden !important;
}
[data-testid="block-container"] {
    padding-top: 0.1rem !important;
    padding-bottom: 0.4rem !important;
    overflow: hidden !important;
    max-height: 100vh !important;
    font-family: 'Libre Baskerville', Georgia, serif !important;
}

/* ═══ SIDEBAR ═══ */
[data-testid="stSidebar"] {
    background: #1a1208 !important;
    border-right: 3px double #c9a84c;
}
[data-testid="stSidebar"] * {
    color: #e8dfc9 !important;
    font-family: 'Libre Baskerville', Georgia, serif !important;
}
[data-testid="stSidebar"] .stButton > button {
    background: transparent;
    border: 1px solid #3d2e14;
    color: #d4c89a !important;
    border-radius: 2px;
    text-align: left;
    font-size: 0.52em;
    padding: 7px 10px;
    width: 100%;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    transition: background 0.2s, border-color 0.2s;
    font-family: 'Libre Baskerville', Georgia, serif !important;
}
[data-testid="stSidebar"] .stButton > button:hover {
    background: #2c1f0a;
    border-color: #c9a84c;
}
.sidebar-title {
    font-family: 'Playfair Display', Georgia, serif;
    font-size: 1.1em;
    font-weight: 900;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    color: #c9a84c !important;
    border-bottom: 1px solid #3d2e14;
    padding-bottom: 8px;
    margin-bottom: 12px;
}
.hist-bar-wrap {
    margin: -4px 0 10px 0;
}
.hist-bar-track {
    background: #2c1f0a;
    border-radius: 0;
    height: 3px;
    overflow: hidden;
    margin-bottom: 2px;
}
.hist-bar-fill { height: 100%; }
.hist-meta {
    font-size: 0.67em;
    color: #6b5a3e !important;
    font-style: italic;
}

/* ═══ MASTHEAD ═══ */
.masthead {
    text-align: center;
    border-top: 4px solid #1a1208;
    border-bottom: 1px solid #1a1208;
    padding: 8px 0 6px;
    margin-bottom: 10px;
    position: relative;
}
.masthead::after {
    content: '';
    display: block;
    border-bottom: 3px solid #1a1208;
    margin-top: 4px;
}
.masthead-tag {
    font-family: 'Libre Baskerville', Georgia, serif;
    font-size: 0.62em;
    letter-spacing: 0.35em;
    text-transform: uppercase;
    color: #5a4a2e;
}
.masthead-title {
    font-family: 'Playfair Display', Georgia, serif;
    font-size: 2.1em;
    font-weight: 900;
    color: #1a1208;
    letter-spacing: -0.01em;
    line-height: 1;
    margin: 2px 0;
}
.masthead-sub {
    font-family: 'Libre Baskerville', Georgia, serif;
    font-size: 0.62em;
    color: #8a7355;
    font-style: italic;
    letter-spacing: 0.08em;
}

/* ═══ VERDICT ═══ */
.verdict-wrap {
    border-left: 5px solid;
    padding: 10px 14px;
    margin-bottom: 10px;
    background: #fffdf6;
    border-top: 1px solid #d4c9a8;
    border-right: 1px solid #d4c9a8;
    border-bottom: 1px solid #d4c9a8;
}
.verdict-score {
    font-family: 'Playfair Display', Georgia, serif;
    font-size: 1.2em;
    font-weight: 900;
    margin-bottom: 3px;
}
.verdict-align {
    font-size: 0.75em;
    color: #5a4a2e;
    font-style: italic;
    margin-bottom: 6px;
}
.verdict-text {
    font-family: 'Libre Baskerville', Georgia, serif;
    font-size: 0.85em;
    line-height: 1.6;
    color: #1a1208;
}

/* ═══ SECTION HEADER (style colonne de journal) ═══ */
.col-header {
    font-family: 'Playfair Display', Georgia, serif;
    font-size: 0.88em;
    font-weight: 700;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    color: #1a1208;
    border-top: 3px solid #1a1208;
    border-bottom: 1px solid #1a1208;
    padding: 4px 0;
    margin-bottom: 8px;
}

/* ═══ ZONE SCROLLABLE CARTES ═══ */
.cards-scroll {
    max-height: 300px;
    overflow-y: auto;
    overflow-x: hidden;
    padding-right: 4px;
}
.cards-scroll::-webkit-scrollbar { width: 4px; }
.cards-scroll::-webkit-scrollbar-track { background: #f0ebe0; }
.cards-scroll::-webkit-scrollbar-thumb { background: #c9a84c; border-radius: 2px; }

/* ═══ TWEET / BLUESKY CARD ═══ */
.tweet-card {
    border: 1px solid #c9d8e8;
    border-left: 3px solid #1d9bf0;
    background: #f7fbff;
    padding: 10px 12px;
    margin-bottom: 8px;
}
.tweet-card:hover { background: #eef6ff; }
.tweet-header {
    display: flex;
    align-items: center;
    gap: 8px;
    margin-bottom: 7px;
}
.tweet-avatar {
    width: 30px; height: 30px;
    border-radius: 50%;
    background: linear-gradient(135deg, #1d9bf0, #0a6fc2);
    display: flex; align-items: center; justify-content: center;
    font-size: 13px; flex-shrink: 0;
}
.tweet-meta { flex: 1; min-width: 0; }
.tweet-name {
    font-family: 'Libre Baskerville', Georgia, serif;
    font-size: 0.78em;
    font-weight: 700;
    color: #1a1208;
}
.tweet-handle { font-size: 0.68em; color: #6b8299; }
.sim-badge {
    font-size: 0.68em;
    font-weight: 700;
    padding: 2px 7px;
    border-radius: 1px;
    flex-shrink: 0;
    font-family: 'Libre Baskerville', Georgia, serif;
}
.tweet-body {
    font-family: 'Libre Baskerville', Georgia, serif;
    font-size: 0.8em;
    line-height: 1.55;
    color: #1a1208;
}

.article-date {
    font-size: 0.62em;
    color: #8a7355;
    font-style: italic;
    margin-left: auto;
}

/* ═══ QUESTION + NOMS CLIQUABLES (zone Wikipédia) ═══ */
.wiki-question {
    font-family: 'Libre Baskerville', Georgia, serif;
    font-size: 0.78em;
    line-height: 1.6;
    color: #1a1208;
    border: 1px solid #c9c2d8;
    border-left: 3px solid #5a5a8a;
    background: #fbfaff;
    padding: 9px 12px;
    margin-bottom: 10px;
}
.wiki-noun-link {
    color: #3d3d6b;
    text-decoration: none;
    border-bottom: 1px dotted #5a5a8a;
    transition: background 0.15s;
}
.wiki-noun-link:hover { background: #ece9f7; }

/* ═══ ARTICLE CARD (style coupure de presse) ═══ */
.article-card {
    border: 1px solid #c9b87a;
    background: #fffdf6;
    padding: 10px 12px;
    margin-bottom: 8px;
    display: block;
    color: inherit;
    text-decoration: none;
    transition: background 0.15s;
}
.article-card:hover { background: #fdf8e8; }
.article-source {
    display: flex;
    align-items: center;
    gap: 5px;
    margin-bottom: 5px;
}
.article-domain {
    font-family: 'Libre Baskerville', Georgia, serif;
    font-size: 0.65em;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    color: #5a4a2e;
    border-bottom: 1px solid #c9b87a;
    padding-bottom: 1px;
}
.article-title {
    font-family: 'Playfair Display', Georgia, serif;
    font-size: 0.9em;
    font-weight: 700;
    line-height: 1.3;
    color: #1a1208;
    margin-bottom: 5px;
}
.article-snippet {
    font-family: 'Libre Baskerville', Georgia, serif;
    font-size: 0.75em;
    color: #4a3e2a;
    line-height: 1.5;
    font-style: italic;
}

/* ═══ STATS ═══ */
.stat-row {
    display: flex;
    gap: 8px;
    margin-top: 8px;
    border-top: 1px solid #d4c9a8;
    padding-top: 6px;
}
.stat-badge {
    font-family: 'Libre Baskerville', Georgia, serif;
    font-size: 0.72em;
    font-weight: 700;
    padding: 2px 10px;
    border-radius: 1px;
    border: 1px solid currentColor;
}
.stat-sim  { color: #1a5c2e; background: #eaf6ee; }
.stat-con  { color: #7a1a1a; background: #faeaea; }

/* ═══ JAUGE ═══ */
.gauge-wrap { position: relative; margin: 4px 0 28px 0; }
.gauge-track {
    height: 14px;
    border-radius: 0;
    background: linear-gradient(to right, #b91c1c 0%, #d97706 40%, #15803d 70%, #15803d 100%);
    border: 1px solid #1a1208;
}
.gauge-thumb {
    position: absolute;
    top: 50%;
    transform: translate(-50%, -50%);
    width: 28px; height: 28px;
    border-radius: 50%;
    border: 2px solid #1a1208;
    display: flex; align-items: center; justify-content: center;
    font-size: 0.62em;
    font-weight: 800;
    font-family: 'Playfair Display', Georgia, serif;
    box-shadow: 0 2px 6px rgba(0,0,0,0.3);
    background: white;
    color: #1a1208;
}
.gauge-labels {
    display: flex;
    justify-content: space-between;
    font-size: 0.67em;
    color: #8a7355;
    margin-top: 4px;
    font-style: italic;
    font-family: 'Libre Baskerville', Georgia, serif;
}

/* ═══ ZONE SAISIE — Liquid Glass Apple style ═══ */

/* Le verre est sur le CONTENEUR, pas sur le textarea */
[data-testid="stTextArea"] > div,
[data-testid="stTextArea"] > div > div {
    background: linear-gradient(
        160deg,
        rgba(255, 255, 255, 0.38) 0%,
        rgba(255, 255, 255, 0.12) 60%,
        rgba(255, 255, 255, 0.20) 100%
    ) !important;
    backdrop-filter: blur(28px) saturate(160%) brightness(1.04) !important;
    -webkit-backdrop-filter: blur(28px) saturate(160%) brightness(1.04) !important;
    border-radius: 32px !important;
    border: none !important;
    box-shadow:
        inset 0 1.5px 0 rgba(255, 255, 255, 0.85),
        inset 0 -1px 0 rgba(255, 255, 255, 0.20),
        0 6px 24px rgba(26, 18, 8, 0.07),
        0 1px 3px rgba(26, 18, 8, 0.04) !important;
    overflow: hidden !important;
    transition: box-shadow 0.3s ease, background 0.3s ease !important;
}

/* Focus : éclat légèrement plus vif */
[data-testid="stTextArea"] > div:focus-within,
[data-testid="stTextArea"] > div > div:focus-within {
    background: linear-gradient(
        160deg,
        rgba(255, 255, 255, 0.50) 0%,
        rgba(255, 255, 255, 0.18) 60%,
        rgba(255, 255, 255, 0.28) 100%
    ) !important;
    box-shadow:
        inset 0 1.5px 0 rgba(255, 255, 255, 0.95),
        inset 0 -1px 0 rgba(255, 255, 255, 0.30),
        0 10px 36px rgba(26, 18, 8, 0.10),
        0 2px 6px rgba(26, 18, 8, 0.05) !important;
}

/* Le textarea lui-même : complètement transparent */
[data-testid="stTextArea"] textarea {
    background: transparent !important;
    border: none !important;
    border-radius: 0 !important;
    box-shadow: none !important;
    outline: none !important;
    font-family: 'Libre Baskerville', Georgia, serif !important;
    font-size: 0.9em !important;
    color: #1a1208 !important;
    resize: none !important;
    padding: 20px 28px !important;
}
[data-testid="stTextArea"] textarea:focus {
    background: transparent !important;
    border: none !important;
    box-shadow: none !important;
    outline: none !important;
}
[data-testid="stTextArea"] textarea::placeholder {
    color: rgba(90, 74, 46, 0.38) !important;
    font-style: italic;
}

/* ═══ BOUTON ANALYSER ═══ */
[data-testid="stFormSubmitButton"] > button {
    background: #1a1208 !important;
    color: #f8f4ea !important;
    border: none !important;
    border-radius: 2px !important;
    font-family: 'Playfair Display', Georgia, serif !important;
    font-weight: 700 !important;
    letter-spacing: 0.08em !important;
    font-size: 0.85em !important;
}
[data-testid="stFormSubmitButton"] > button:hover {
    background: #2c1f0a !important;
    color: #c9a84c !important;
}

/* ═══ ÉTAT VIDE ═══ */
.empty-state {
    text-align: center;
    padding: 30px 20px;
    color: #8a7355;
    font-family: 'Libre Baskerville', Georgia, serif;
}
.empty-state .big-icon { font-size: 2.5em; margin-bottom: 8px; }
.empty-state h3 {
    font-family: 'Playfair Display', Georgia, serif;
    color: #4a3e2a;
    font-size: 1.1em;
    margin-bottom: 6px;
}

/* ═══ MASQUER BRANDING STREAMLIT ═══ */
#MainMenu { visibility: hidden; }
footer    { visibility: hidden; }
.stDeployButton { display: none; }
header[data-testid="stHeader"] { background: transparent !important; }
</style>
""", unsafe_allow_html=True)


# ── Helpers ───────────────────────────────────────────────────────────────────

def label_color(label: str) -> str:
    return {"reliable": "#15803d", "unreliable": "#b91c1c", "suspect": "#b45309"}.get(label, "#5a4a2e")


def bluesky_url(uri: str) -> str:
    m = re.match(r"at://([^/]+)/[^/]+/(.+)", uri or "")
    if m:
        did, rkey = m.groups()
        return f"https://bsky.app/profile/{did}/post/{rkey}"
    return ""


def sim_badge_style(sim: float) -> tuple[str, str]:
    if sim >= 0.55:
        return "#eaf6ee", "#1a5c2e"
    if sim >= 0.35:
        return "#fef3cd", "#92400e"
    return "#f5f0e8", "#5a4a2e"


def esc(value: str) -> str:
    """Échappe le HTML et neutralise les retours à la ligne (qui casseraient le bloc markdown)."""
    return html_lib.escape(str(value or "")).replace("\n", " ").replace("\r", " ")


def tweets_html(sources: list[dict]) -> str:
    if not sources:
        return '<p style="font-style:italic;color:#8a7355;font-size:0.82em;">Aucun post Bluesky trouvé.</p>'
    cards = []
    for src in sources:
        sim   = src.get("similarity", 0)
        text  = src.get("text", "")[:300]
        uri   = src.get("uri", "")
        url   = bluesky_url(uri)
        bg, fg = sim_badge_style(sim)
        ellipsis = "…" if len(src.get("text", "")) > 300 else ""
        card = (
            f'<div class="tweet-card">'
            f'<div class="tweet-header">'
            f'<div class="tweet-avatar">🦋</div>'
            f'<div class="tweet-meta">'
            f'<div class="tweet-name">Bluesky · Média vérifié</div>'
            f'<div class="tweet-handle">source fiable</div>'
            f'</div>'
            f'<div class="sim-badge" style="background:{bg};color:{fg};">{sim:.0%}</div>'
            f'</div>'
            f'<div class="tweet-body">{esc(text)}{ellipsis}</div>'
            f'</div>'
        )
        if url:
            card = f'<a href="{esc(url)}" target="_blank" style="text-decoration:none;">{card}</a>'
        cards.append(card)
    return "".join(cards)


def articles_html(articles: list[dict]) -> str:
    if not articles:
        return '<p style="font-style:italic;color:#8a7355;font-size:0.82em;">Aucun article trouvé.</p>'
    cards = []
    for a in articles:
        title   = esc(a.get("title", "Sans titre"))
        url     = esc(a.get("url", "#"))
        snippet = a.get("snippet", "")[:180]
        ellipsis = "…" if len(a.get("snippet", "")) > 180 else ""
        domain  = esc(a.get("source_domain", ""))
        date    = esc((a.get("date") or "")[:10])
        favicon = f"https://www.google.com/s2/favicons?domain={domain}&amp;sz=32"
        date_html = f'<span class="article-date">{date}</span>' if date else ""
        cards.append(
            f'<a href="{url}" target="_blank" class="article-card">'
            f'<div class="article-source">'
            f'<img src="{favicon}" width="12" height="12" '
            f'onerror="this.style.display=\'none\'" style="vertical-align:middle;"/>'
            f'<span class="article-domain">{domain}</span>'
            f'{date_html}'
            f'</div>'
            f'<div class="article-title">{title}</div>'
            f'<div class="article-snippet">{esc(snippet)}{ellipsis}</div>'
            f'</a>'
        )
    return "".join(cards)


@st.cache_resource(show_spinner=False)
def get_nlp():
    return spacy.load("fr_core_news_sm")


@st.cache_data(show_spinner=False, max_entries=2000)
def _wiki_url_for(word: str) -> str | None:
    """Recherche Wikipédia pour un seul mot — mis en cache pour éviter les requêtes répétées."""
    result = search_wikipedia(word)
    return result["url"] if result else None


def linkify_nouns(text: str) -> str:
    """
    Rend chaque nom propre et nom commun du texte cliquable vers sa page Wikipédia
    (si elle existe). Les entités multi-mots (ex: "Emmanuel Macron") sont liées en un
    seul lien plutôt qu'un lien par mot. Les mots sans page correspondante restent
    du texte simple.
    """
    if not text:
        return ""

    doc = get_nlp()(text)

    # Entités nommées multi-mots : un seul lien pour toute l'entité (ex: "Donald Trump")
    entity_start = {ent.start: ent for ent in doc.ents}
    covered      = {i for ent in doc.ents for i in range(ent.start, ent.end)}

    candidates = {ent.text for ent in doc.ents}
    candidates |= {t.text for t in doc if t.i not in covered and t.pos_ in NOUN_POS and len(t.text) > 2}

    links: dict[str, str | None] = {}
    if candidates:
        candidates = list(candidates)
        with ThreadPoolExecutor(max_workers=8) as executor:
            links = dict(zip(candidates, executor.map(_wiki_url_for, candidates)))

    parts = []
    i = 0
    while i < len(doc):
        ent = entity_start.get(i)
        if ent is not None:
            surface = doc.text[ent.start_char:ent.end_char]
            url = links.get(ent.text)
            if url:
                parts.append(f'<a href="{esc(url)}" target="_blank" class="wiki-noun-link">{esc(surface)}</a>')
            else:
                parts.append(esc(surface))
            parts.append(esc(doc[ent.end - 1].whitespace_))
            i = ent.end
            continue

        tok = doc[i]
        url = links.get(tok.text) if tok.pos_ in NOUN_POS else None
        if url:
            parts.append(f'<a href="{esc(url)}" target="_blank" class="wiki-noun-link">{esc(tok.text)}</a>')
        else:
            parts.append(esc(tok.text))
        parts.append(esc(tok.whitespace_))
        i += 1
    return "".join(parts)


def stat_row_html(similar: int, contra: int) -> str:
    s = "s" if similar > 1 else ""
    c = "ent" if contra > 1 else ""
    return f"""
    <div class="stat-row">
      <span class="stat-badge stat-sim">✓ {similar} similaire{s}</span>
      <span class="stat-badge stat-con">✗ {contra} qui contredit{c}</span>
    </div>"""


def gauge_html(score: int, label: str) -> str:
    color = label_color(label)
    return f"""
    <div class="gauge-wrap">
      <div class="gauge-track"></div>
      <div class="gauge-thumb" style="left:{score}%;border-color:{color};color:{color};">{score}</div>
    </div>
    <div class="gauge-labels">
      <span>0 — Non fiable</span><span>40 — Suspect</span>
      <span>70 — Fiable</span><span>100</span>
    </div>"""


# ── RAG service (chargé une seule fois) ──────────────────────────────────────
@st.cache_resource(show_spinner=False)
def get_service():
    return RAGCredibilityService()


# ── Session state ─────────────────────────────────────────────────────────────
if "history"  not in st.session_state: st.session_state.history  = []
if "current"  not in st.session_state: st.session_state.current  = None


# ── Sidebar — Historique ──────────────────────────────────────────────────────
with st.sidebar:
    st.markdown('<div class="sidebar-title">&#128240; Historique</div>', unsafe_allow_html=True)

    if not st.session_state.history:
        st.markdown(
            '<div style="color:#6b5a3e;font-size:0.78em;font-style:italic;">'
            "Vos analyses apparaîtront ici.</div>",
            unsafe_allow_html=True,
        )
    else:
        for idx, item in enumerate(reversed(st.session_state.history)):
            res    = item["result"]
            score  = res.get("credibility_score", 0)
            label  = res.get("credibility_label", "suspect")
            icon   = LABEL_ICON.get(label, "⚠️")
            color  = label_color(label)
            preview = item["news"][:44] + "…" if len(item["news"]) > 44 else item["news"]

            if st.button(f"{icon}  {preview}", key=f"hist_{idx}", use_container_width=True):
                st.session_state.current = item
                st.rerun()

            st.markdown(f"""
            <div class="hist-bar-wrap">
              <div class="hist-bar-track">
                <div class="hist-bar-fill" style="width:{score}%;background:{color};"></div>
              </div>
              <div class="hist-meta">{score} pts — {LABEL_FR.get(label, label)}</div>
            </div>""", unsafe_allow_html=True)


# ── Masthead ──────────────────────────────────────────────────────────────────
st.markdown("""
<div class="masthead">
  <div class="masthead-tag">— Intelligence Artificielle & Vérification des faits —</div>
  <div class="masthead-title">FACT CHECKER IA</div>
  <div class="masthead-sub">Bluesky · Presse internationale · Mistral AI</div>
</div>
""", unsafe_allow_html=True)


# ── Zone résultat ─────────────────────────────────────────────────────────────
ALIGN_FR = {
    "confirmed":    "confirmée par les sources",
    "contradicted": "contredite par les sources",
    "not_covered":  "non couverte par les sources disponibles",
}

if st.session_state.current:
    res          = st.session_state.current["result"]
    score        = res.get("credibility_score", 0)
    label        = res.get("credibility_label", "suspect")
    justif       = res.get("justification", "")
    alignment    = res.get("alignment", "not_covered")
    sources_used = res.get("sources_used", [])
    web_articles = res.get("web_articles", [])
    web_error    = res.get("web_error")
    color        = label_color(label)
    icon         = LABEL_ICON.get(label, "⚠️")

    # 0. News soumise
    news_preview = st.session_state.current["news"]
    st.markdown(f"""
    <div style="font-family:'Libre Baskerville',Georgia,serif;
                font-size:0.8em;color:#5a4a2e;
                border-left:3px solid #c9b87a;
                padding:6px 12px;margin-bottom:8px;
                font-style:italic;">
      <span style="font-size:0.75em;font-weight:700;letter-spacing:0.1em;
                   text-transform:uppercase;font-style:normal;color:#8a7355;">
        News analysée
      </span><br/>
      {news_preview}
    </div>
    """, unsafe_allow_html=True)

    # 1. Verdict LLM
    st.markdown(f"""
    <div class="verdict-wrap" style="border-left-color:{color};">
      <div class="verdict-score" style="color:{color};">
        {icon} {LABEL_FR.get(label, label)} — {score}/100
      </div>
      <div class="verdict-align">Information {ALIGN_FR.get(alignment, alignment)}</div>
      <div class="verdict-text">{justif}</div>
    </div>
    """, unsafe_allow_html=True)

    # 2. Deux colonnes scrollables
    col_l, col_r = st.columns(2, gap="medium")

    similar_posts    = len(sources_used)
    contra_posts     = 1 if alignment == "contradicted" else 0
    similar_articles = len(web_articles)
    contra_articles  = 1 if alignment == "contradicted" else 0

    with col_l:
        st.markdown("""
        <div class="col-header">🦋&nbsp; Posts Bluesky</div>
        """, unsafe_allow_html=True)
        st.markdown(f"""
        <div class="cards-scroll">{tweets_html(sources_used)}</div>
        {stat_row_html(similar_posts, contra_posts)}
        """, unsafe_allow_html=True)

    with col_r:
        st.markdown("""
        <div class="col-header">📖&nbsp; Wikipédia</div>
        """, unsafe_allow_html=True)
        st.markdown(
            f'<div class="wiki-question">{linkify_nouns(news_preview)}</div>',
            unsafe_allow_html=True,
        )

        st.markdown("""
        <div class="col-header">📰&nbsp; Articles de presse</div>
        """, unsafe_allow_html=True)
        if web_error:
            st.markdown(f"""
            <div style="font-family:'Libre Baskerville',Georgia,serif;font-size:0.8em;
                        border:1px solid #c9b87a;padding:10px;background:#fffdf6;
                        color:#7a4a1a;font-style:italic;">
              ⚠ Recherche web temporairement indisponible.<br/>
              <span style="font-size:0.9em;">DuckDuckGo rate-limit — réessayez dans quelques secondes.</span>
            </div>
            {stat_row_html(0, 0)}
            """, unsafe_allow_html=True)
        else:
            st.markdown(f"""
            <div class="cards-scroll">{articles_html(web_articles)}</div>
            {stat_row_html(similar_articles, contra_articles)}
            """, unsafe_allow_html=True)


else:
    st.markdown("""
    <div class="empty-state">
      <div class="big-icon">🔍</div>
      <h3>Prêt à analyser une news</h3>
      <p style="font-size:0.83em;">
        Saisissez le texte d'une actualité ci-dessous.<br/>
        L'IA croisera posts Bluesky et articles de presse pour évaluer sa crédibilité.
      </p>
    </div>
    """, unsafe_allow_html=True)


# ── Zone de saisie ────────────────────────────────────────────────────────────
st.markdown(
    '<div style="border-top:2px solid #1a1208;margin-top:6px;"></div>',
    unsafe_allow_html=True,
)

with st.form("news_form", clear_on_submit=True):
    news_input = st.text_area(
        "news_input",
        placeholder="Saisissez ou collez ici le texte d'une news à vérifier…",
        height=68,
        label_visibility="collapsed",
    )
    _, col_btn = st.columns([5, 1])
    with col_btn:
        submitted = st.form_submit_button("Analyser ›", use_container_width=True, type="primary")

if submitted and news_input.strip():
    if st.session_state.current:
        st.session_state.history.append(st.session_state.current)

    with st.spinner("Analyse en cours…"):
        try:
            service = get_service()
            result  = service.score(news_input.strip())
            st.session_state.current = {"news": news_input.strip(), "result": result}
        except FileNotFoundError as e:
            st.error(f"Index RAG introuvable. Lancez d'abord :\n```\npython scripts/8_build_rag_index.py\n```")
        except Exception as e:
            st.error(f"Erreur : {e}")
    st.rerun()

elif submitted:
    st.warning("Entrez une news avant de lancer l'analyse.")