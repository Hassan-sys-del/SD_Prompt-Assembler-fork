from pathlib import Path
import sys

APP_ROOT = Path(__file__).resolve().parent
SRC_DIR = APP_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

try:
    from prompt_manager import main
except ImportError:
    from src.prompt_manager import main

if __name__ == "__main__":
    main()
