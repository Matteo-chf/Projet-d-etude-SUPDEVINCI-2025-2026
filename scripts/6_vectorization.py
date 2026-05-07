import subprocess
import sys
from pathlib import Path

kedro_project = Path(__file__).parent.parent / "pipeline-kedro"

result = subprocess.run(
    [sys.executable, "-m", "kedro", "run", "--pipeline", "vectorization"],
    cwd=kedro_project,
)
sys.exit(result.returncode)
