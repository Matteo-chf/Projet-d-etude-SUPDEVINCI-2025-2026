# Étape 9 — Analyse de crédibilité par RAG + Claude
# Interface CLI : saisie d'une news → score 0-100 + label + justification + sources citées
#
# Prérequis (dans l'ordre) :
#   1. python scripts/5_label_sources.py    → labélise les sources MongoDB
#   2. python scripts/8_build_rag_index.py  → construit l'index vectoriel
#   3. ANTHROPIC_API_KEY dans le .env
#
# Usage :
#   python scripts/9_rag_credibility.py                           → mode interactif
#   python scripts/9_rag_credibility.py "Texte de la news ici."  → argument direct
#   python scripts/9_rag_credibility.py --top-k 8 "Texte..."    → top-k personnalisé

import sys       # lecture des arguments CLI et encodage Windows
import argparse  # parsing des arguments --top-k

# Force l'affichage UTF-8 sur Windows (pour les barres █ et les emojis)
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# Import du service RAG et des constantes d'affichage
sys.path.insert(0, __file__.replace("9_rag_credibility.py", ""))
from rag_service import RAGCredibilityService, LABEL_FR, LABEL_ICON


def display(result: dict, original_text: str):
    """Affiche le résultat de l'analyse : score, label, justification et sources."""
    sep = "=" * 64
    print(f"\n{sep}")
    print("  ANALYSE DE CRÉDIBILITÉ — RAG + Mistral")
    print(sep)

    preview = original_text[:120] + ("…" if len(original_text) > 120 else "")
    print(f"\n  Texte : {preview}\n")

    if "error" in result:
        print(f"  ⚠  Erreur : {result['error']}")
        if "raw" in result:
            print(f"  Réponse brute : {result['raw']}")
        print(sep + "\n")
        return

    score     = result.get("credibility_score", 0)
    label     = result.get("credibility_label", "suspect")
    justif    = result.get("justification", "")
    alignment = result.get("alignment", "")
    avg_sim   = result.get("avg_similarity", 0)
    sources   = result.get("sources_used", [])

    # Barre de progression visuelle : 40 caractères = 100 %
    filled = int(score * 40 / 100)
    bar    = "█" * filled + "░" * (40 - filled)

    ALIGN_FR = {"confirmed": "CONFIRMÉE", "contradicted": "CONTREDITE", "not_covered": "NON COUVERTE"}

    print(f"  Score de crédibilité : {score}/100")
    print(f"  [{bar}]")
    print(f"\n  {LABEL_ICON.get(label, '')}  {label.upper()} — {LABEL_FR.get(label, '')}")
    if alignment:
        print(f"  Alignement avec les sources fiables : {ALIGN_FR.get(alignment, alignment)}")
    print(f"  Similarité moyenne avec la base : {avg_sim:.0%}\n")
    print(f"  Analyse : {justif}\n")

    # Sources MongoDB (posts Bluesky fiables)
    if sources:
        print("  Sources base locale (Bluesky) :")
        for i, src in enumerate(sources, 1):
            sim     = src.get("similarity", 0)
            snippet = src.get("text", "")[:80].replace("\n", " ")
            print(f"    {i}. ✅ sim={sim:.0%}  {snippet}…")

    # Articles web trouvés par DuckDuckGo
    web_articles = result.get("web_articles", [])
    if web_articles:
        print(f"\n  Articles web trouvés ({len(web_articles)}) :")
        for i, a in enumerate(web_articles, 1):
            domain  = a.get("source_domain", "")
            title   = a.get("title", "")[:70]
            url     = a.get("url", "")
            print(f"    {i}. 🌐 [{domain}] {title}")
            print(f"       {url}")
    elif "web_articles" in result:
        print("\n  Aucun article web trouvé pour ce sujet.")

    print(sep + "\n")


def main():
    parser = argparse.ArgumentParser(
        description="Analyse la crédibilité d'une information par RAG + Claude"
    )
    parser.add_argument("text",     nargs="*", help="Texte de la news à analyser")
    parser.add_argument("--top-k",  type=int,  default=5,    help="Nombre de sources MongoDB à récupérer (défaut: 5)")
    parser.add_argument("--no-web", action="store_true",     help="Désactiver la recherche web")
    args = parser.parse_args()

    print("\n╔══════════════════════════════════════════════════════════╗")
    print("║   Score de crédibilité — RAG + Mistral                  ║")
    print("╚══════════════════════════════════════════════════════════╝\n")

    # Chargement du service RAG (modèle MiniLM + index numpy)
    try:
        service = RAGCredibilityService()
    except FileNotFoundError as e:
        print(f"⚠  {e}")
        sys.exit(1)

    # Mode argument : texte passé directement en ligne de commande
    use_web = not args.no_web

    if args.text:
        text   = " ".join(args.text)
        result = service.score(text, top_k=args.top_k, use_web=use_web)
        display(result, text)
        return

    # Mode interactif : boucle de saisie jusqu'à Ctrl+C
    print("Entrez une news pour obtenir son score de crédibilité.")
    print("(Ctrl+C pour quitter)\n")

    while True:
        try:
            text = input(">>> News : ").strip()
            if not text:
                continue
            print("Analyse en cours…")
            result = service.score(text, top_k=args.top_k, use_web=use_web)
            display(result, text)
        except KeyboardInterrupt:
            print("\nAu revoir.")
            break


if __name__ == "__main__":
    main()
