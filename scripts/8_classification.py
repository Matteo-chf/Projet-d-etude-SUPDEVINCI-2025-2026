import subprocess
import sys
from pathlib import Path

kedro_project = Path(__file__).parent.parent / "pipeline-kedro"

# Etape 8 : emotion (VADER) + classification (LogisticRegression) reliable/unreliable
result = subprocess.run(
    [sys.executable, "-m", "kedro", "run", "--pipeline", "classification"],
    cwd=kedro_project,
)
sys.exit(result.returncode)
