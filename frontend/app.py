import os
import sys
import re
import streamlit as st

# --- Paths ---
ROOT_DIR    = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS_DIR = os.path.join(ROOT_DIR, "scripts")
sys.path.insert(0, SCRIPTS_DIR)

from rag_service import RAGCredibilityService, LABEL_FR, LABEL_ICON

# ──────────────────────────────────────────────
# Page config
# ──────────────────────────────────────────────
st.set_page_config(
    page_title="Fact-Checker IA",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ──────────────────────────────────────────────
# CSS global
# ──────────────────────────────────────────────
st.markdown("""
<style>
/* ── Sidebar ── */
[data-testid="stSidebar"] {
    background: #0f172a;
    border-right: 1px solid #1e293b;
}
[data-testid="stSidebar"] * { color: #e2e8f0 !important; }
[data-testid="stSidebar"] .stButton > button {
    background: transparent;
    border: 1px solid #1e293b;
    color: #cbd5e1 !important;
    border-radius: 10px;
    text-align: left;
    font-size: 0.82em;
    padding: 8px 12px;
    width: 100%;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    transition: background 0.2s, border-color 0.2s;
}
[data-testid="stSidebar"] .stButton > button:hover {
    background: #1e293b;
    border-color: #334155;
}

/* ── Tweet card (Bluesky) ── */
.tweet-card {
    border: 1px solid #bae6fd;
    border-radius: 16px;
    padding: 16px;
    margin-bottom: 14px;
    background: linear-gradient(135deg, #f0f9ff 0%, #e0f2fe 100%);
    transition: box-shadow 0.2s, transform 0.15s;
    cursor: default;
}
.tweet-card:hover {
    box-shadow: 0 6px 24px rgba(0, 133, 255, 0.12);
    transform: translateY(-2px);
}

/* ── Article preview card ── */
.article-card {
    border: 1px solid #e2e8f0;
    border-radius: 14px;
    padding: 16px;
    margin-bottom: 14px;
    background: #fff;
    transition: box-shadow 0.2s, transform 0.15s, border-color 0.2s;
    display: block;
}
.article-card:hover {
    box-shadow: 0 6px 20px rgba(0,0,0,0.09);
    border-color: #94a3b8;
    transform: translateY(-2px);
}

/* ── Stat badges ── */
.stat-row { display: flex; gap: 12px; margin-top: 14px; flex-wrap: wrap; }
.stat-badge {
    padding: 5px 14px;
    border-radius: 999px;
    font-size: 0.8em;
    font-weight: 600;
    display: inline-flex;
    align-items: center;
    gap: 5px;
}
.stat-similar  { background: #dcfce7; color: #166534; }
.stat-contra   { background: #fee2e2; color: #991b1b; }

/* ── Verdict banner ── */
.verdict-banner {
    border-radius: 12px;
    padding: 18px 22px;
    margin-bottom: 24px;
    border-left: 5px solid;
}

/* ── Section titles ── */
.section-title {
    font-size: 1.05em;
    font-weight: 700;
    margin-bottom: 14px;
    display: flex;
    align-items: center;
    gap: 8px;
    color: #1e293b;
}

/* ── Input zone ── */
[data-testid="stTextArea"] textarea {
    border-radius: 14px !important;
    border: 2px solid #e2e8f0 !important;
    font-size: 0.97em !important;
    resize: none;
    transition: border-color 0.2s !important;
}
[data-testid="stTextArea"] textarea:focus {
    border-color: #3b82f6 !important;
    box-shadow: 0 0 0 3px rgba(59,130,246,0.1) !important;
}

/* ── Veracity gauge ── */
.gauge-wrap { position: relative; margin: 8px 0 36px 0; }
.gauge-track {
    height: 18px;
    border-radius: 999px;
    background: linear-gradient(to right, #ef4444 0%, #f59e0b 40%, #22c55e 70%);
}
.gauge-thumb {
    position: absolute;
    top: 50%;
    transform: translate(-50%, -50%);
    width: 36px;
    height: 36px;
    border-radius: 50%;
    border: 3px solid white;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 0.7em;
    font-weight: 800;
    box-shadow: 0 2px 8px rgba(0,0,0,0.18);
}
.gauge-labels {
    display: flex;
    justify-content: space-between;
    font-size: 0.77em;
    color: #94a3b8;
    margin-top: 6px;
}

/* ── Empty state ── */
.empty-state {
    text-align: center;
    padding: 60px 20px;
    color: #94a3b8;
}
.empty-state .big-icon { font-size: 3.5em; margin-bottom: 12px; }
.empty-state h3 { color: #64748b; font-size: 1.1em; margin-bottom: 8px; }

/* ── Hide Streamlit branding ── */
#MainMenu { visibility: hidden; }
footer    { visibility: hidden; }
.stDeployButton { display: none; }
</style>
""", unsafe_allow_html=True)


# ──────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────

def label_color(label: str) -> str:
    return {"reliable": "#22c55e", "unreliable": "#ef4444", "suspect": "#f59e0b"}.get(label, "#94a3b8")


def bluesky_url(uri: str) -> str:
    """Convert AT URI → bsky.app URL."""
    m = re.match(r"at://([^/]+)/[^/]+/(.+)", uri or "")
    if m:
        did, rkey = m.groups()
        return f"https://bsky.app/profile/{did}/post/{rkey}"
    return ""


def sim_badge_color(sim: float) -> str:
    if sim >= 0.55:
        return "#22c55e"
    if sim >= 0.35:
        return "#f59e0b"
    return "#94a3b8"


def render_tweet(src: dict):
    sim   = src.get("similarity", 0)
    text  = src.get("text", "")
    uri   = src.get("uri", "")
    url   = bluesky_url(uri)
    color = sim_badge_color(sim)

    link_open  = f'<a href="{url}" target="_blank" style="text-decoration:none;color:inherit;">' if url else ""
    link_close = "</a>" if url else ""

    st.markdown(f"""
    {link_open}
    <div class="tweet-card">
      <div style="display:flex;align-items:center;gap:10px;margin-bottom:10px;">
        <div style="width:38px;height:38px;border-radius:50%;
                    background:linear-gradient(135deg,#0085ff,#00c2ff);
                    display:flex;align-items:center;justify-content:center;
                    font-size:17px;flex-shrink:0;">🦋</div>
        <div style="flex:1;min-width:0;">
          <div style="font-weight:700;font-size:0.88em;color:#0f172a;">Média vérifié Bluesky</div>
          <div style="font-size:0.75em;color:#64748b;">source fiable</div>
        </div>
        <div style="background:{color}22;color:{color};
                    padding:3px 10px;border-radius:999px;
                    font-size:0.75em;font-weight:700;flex-shrink:0;">{sim:.0%}</div>
      </div>
      <div style="font-size:0.88em;line-height:1.55;color:#1e293b;">
        {text[:300]}{"…" if len(text) > 300 else ""}
      </div>
    </div>
    {link_close}
    """, unsafe_allow_html=True)


def render_article(article: dict):
    title   = article.get("title", "Sans titre")
    url     = article.get("url", "#")
    snippet = article.get("snippet", "")
    domain  = article.get("source_domain", "")
    favicon = f"https://www.google.com/s2/favicons?domain={domain}&sz=32"

    st.markdown(f"""
    <a href="{url}" target="_blank" style="text-decoration:none;">
    <div class="article-card">
      <div style="display:flex;align-items:center;gap:7px;margin-bottom:10px;">
        <img src="{favicon}" width="14" height="14"
             style="border-radius:3px;"
             onerror="this.style.display='none'" />
        <span style="font-size:0.73em;color:#64748b;font-weight:700;
                     text-transform:uppercase;letter-spacing:0.06em;">{domain}</span>
      </div>
      <div style="font-weight:700;font-size:0.92em;line-height:1.4;
                  margin-bottom:8px;color:#0f172a;">{title}</div>
      <div style="font-size:0.82em;color:#475569;line-height:1.5;">
        {snippet[:180]}{"…" if len(snippet) > 180 else ""}
      </div>
    </div>
    </a>
    """, unsafe_allow_html=True)


def render_stat_row(similar: int, contra: int):
    st.markdown(f"""
    <div class="stat-row">
      <span class="stat-badge stat-similar">✓ {similar} similaire{"s" if similar > 1 else ""}</span>
      <span class="stat-badge stat-contra">✗ {contra} qui contredit{"" if contra <= 1 else "ent"}</span>
    </div>
    """, unsafe_allow_html=True)


def render_gauge(score: int, label: str):
    color = label_color(label)
    st.markdown(f"""
    <div class="gauge-wrap">
      <div class="gauge-track"></div>
      <div class="gauge-thumb" style="left:{score}%;background:{color};color:white;">
        {score}
      </div>
    </div>
    <div class="gauge-labels">
      <span>0 — Non fiable</span>
      <span>40 — Suspect</span>
      <span>70 — Fiable</span>
      <span>100</span>
    </div>
    """, unsafe_allow_html=True)


# ──────────────────────────────────────────────
# RAG service (cached, chargé une seule fois)
# ──────────────────────────────────────────────
@st.cache_resource(show_spinner=False)
def get_service():
    return RAGCredibilityService()


# ──────────────────────────────────────────────
# Session state
# ──────────────────────────────────────────────
if "history" not in st.session_state:
    st.session_state.history = []
if "current" not in st.session_state:
    st.session_state.current = None
if "analyzing" not in st.session_state:
    st.session_state.analyzing = False


# ──────────────────────────────────────────────
# Sidebar — Historique
# ──────────────────────────────────────────────
with st.sidebar:
    st.markdown("### 📂 Historique")

    if not st.session_state.history:
        st.markdown(
            '<div style="color:#475569;font-size:0.82em;margin-top:8px;">'
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
            preview = item["news"][:42] + "…" if len(item["news"]) > 42 else item["news"]

            if st.button(f"{icon} {preview}", key=f"hist_{idx}", use_container_width=True):
                st.session_state.current = item
                st.rerun()

            st.markdown(f"""
            <div style="margin:-6px 0 10px 0;">
              <div style="background:#1e293b;border-radius:999px;height:5px;overflow:hidden;">
                <div style="width:{score}%;background:{color};height:100%;border-radius:999px;"></div>
              </div>
              <div style="font-size:0.7em;color:#64748b;margin-top:3px;">
                {score}% — {LABEL_FR.get(label, label)}
              </div>
            </div>
            """, unsafe_allow_html=True)


# ──────────────────────────────────────────────
# Header
# ──────────────────────────────────────────────
st.markdown(
    '<h1 style="margin-bottom:4px;">🔍 Fact-Checker IA</h1>'
    '<p style="color:#64748b;margin-top:0;">Analysez la crédibilité d\'une news grâce à l\'IA, '
    'des posts Bluesky et des articles de presse fiables.</p>',
    unsafe_allow_html=True,
)
st.divider()


# ──────────────────────────────────────────────
# Zone de résultat
# ──────────────────────────────────────────────
if st.session_state.current:
    res          = st.session_state.current["result"]
    score        = res.get("credibility_score", 0)
    label        = res.get("credibility_label", "suspect")
    justif       = res.get("justification", "")
    alignment    = res.get("alignment", "not_covered")
    sources_used = res.get("sources_used", [])
    web_articles = res.get("web_articles", [])
    color        = label_color(label)
    icon         = LABEL_ICON.get(label, "⚠️")

    ALIGN_FR = {
        "confirmed":   "confirmée par les sources",
        "contradicted": "contredite par les sources",
        "not_covered":  "non couverte par les sources disponibles",
    }

    # 1. Verdict + justification LLM
    st.markdown(f"""
    <div class="verdict-banner"
         style="background:{color}0f;border-left-color:{color};">
      <div style="font-size:1.25em;font-weight:800;color:{color};margin-bottom:8px;">
        {icon} {LABEL_FR.get(label, label)} — {score}/100
      </div>
      <div style="font-size:0.82em;color:#64748b;margin-bottom:10px;font-style:italic;">
        Information {ALIGN_FR.get(alignment, alignment)}
      </div>
      <div style="font-size:0.97em;line-height:1.65;color:#1e293b;">{justif}</div>
    </div>
    """, unsafe_allow_html=True)

    # 2. Deux colonnes — Posts Bluesky | Articles web
    col_l, col_r = st.columns(2, gap="large")

    with col_l:
        st.markdown('<div class="section-title">🦋 Posts Bluesky</div>', unsafe_allow_html=True)
        if sources_used:
            for src in sources_used:
                render_tweet(src)
        else:
            st.caption("Aucun post Bluesky trouvé pour cette news.")

        # Compteurs posts
        similar_posts = len(sources_used)
        contra_posts  = 1 if alignment == "contradicted" else 0
        render_stat_row(similar_posts, contra_posts)

    with col_r:
        st.markdown('<div class="section-title">📰 Articles web</div>', unsafe_allow_html=True)
        web_error = res.get("web_error")
        if web_error:
            st.warning(f"⚠️ Recherche web indisponible — DuckDuckGo rate-limit ou réseau.\n\nRéessayez dans quelques secondes.", icon="🌐")
        elif web_articles:
            for article in web_articles:
                render_article(article)
        else:
            st.caption("Aucun article web trouvé pour cette news.")

        # Compteurs articles
        similar_articles = len(web_articles)
        contra_articles  = 1 if alignment == "contradicted" else 0
        render_stat_row(similar_articles, contra_articles)

    st.divider()

    # 3. Barre de véracité
    st.markdown('<div class="section-title">📊 Score de véracité</div>', unsafe_allow_html=True)
    render_gauge(score, label)

else:
    # État vide — pas encore d'analyse
    st.markdown("""
    <div class="empty-state">
      <div class="big-icon">🔍</div>
      <h3>Prêt à analyser une news</h3>
      <p style="font-size:0.88em;">
        Entrez le texte d'une actualité ci-dessous.<br/>
        L'IA croisera des posts Bluesky fiables et des articles de presse pour évaluer sa crédibilité.
      </p>
    </div>
    """, unsafe_allow_html=True)


# ──────────────────────────────────────────────
# Zone de saisie (toujours en bas)
# ──────────────────────────────────────────────
st.markdown("<br/>", unsafe_allow_html=True)

with st.form("news_form", clear_on_submit=True):
    news_input = st.text_area(
        "news_input",
        placeholder="Collez ou tapez une news à vérifier… (ex : \"Le gouvernement annule la réforme des retraites\")",
        height=90,
        label_visibility="collapsed",
    )
    col_left, col_right = st.columns([5, 1])
    with col_right:
        submitted = st.form_submit_button(
            "🔍 Analyser",
            use_container_width=True,
            type="primary",
        )

if submitted and news_input.strip():
    # Archive l'analyse courante dans l'historique
    if st.session_state.current:
        st.session_state.history.append(st.session_state.current)

    with st.spinner("Analyse en cours… (embedding + recherche web + Mistral)"):
        try:
            service = get_service()
            result  = service.score(news_input.strip())
            st.session_state.current = {"news": news_input.strip(), "result": result}
        except FileNotFoundError as e:
            st.error(
                f"Index RAG introuvable.\n\n"
                f"Construisez-le d'abord :\n"
                f"```\npython scripts/8_build_rag_index.py\n```\n\n{e}"
            )
        except Exception as e:
            st.error(f"Erreur lors de l'analyse : {e}")

    st.rerun()

elif submitted and not news_input.strip():
    st.warning("Entrez une news avant de lancer l'analyse.")