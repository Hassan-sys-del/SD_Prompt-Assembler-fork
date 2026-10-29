import sys
from pathlib import Path

APP_ROOT = Path(__file__).resolve().parent
SRC_DIR = APP_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from prompt_manager import main


if __name__ == "__main__":
    main()
