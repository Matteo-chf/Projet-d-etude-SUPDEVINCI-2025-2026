import subprocess
import sys
from pathlib import Path

kedro_project = Path(__file__).parent.parent / "pipeline-kedro"

# Etape 7 : vectorisation TF-IDF du texte nettoye -> vectorized_posts
result = subprocess.run(
    [sys.executable, "-m", "kedro", "run", "--pipeline", "vectorization"],
    cwd=kedro_project,
)
sys.exit(result.returncode)
