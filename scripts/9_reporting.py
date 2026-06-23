import subprocess
import sys
from pathlib import Path

kedro_project = Path(__file__).parent.parent / "pipeline-kedro"

# Etape 9 : rapport de synthese sur les donnees MongoDB
result = subprocess.run(
    [sys.executable, "-m", "kedro", "run", "--pipeline", "reporting"],
    cwd=kedro_project,
)
sys.exit(result.returncode)
