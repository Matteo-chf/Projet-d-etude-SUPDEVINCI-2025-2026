import subprocess
import sys
from pathlib import Path

kedro_project = Path(__file__).parent.parent / "pipeline-kedro"

# Etape 6 : nettoyage du texte brut MongoDB -> cleaned_bluesky_posts
result = subprocess.run(
    [sys.executable, "-m", "kedro", "run", "--pipeline", "nlp_cleaning"],
    cwd=kedro_project,
)
sys.exit(result.returncode)
