from pathlib import Path
import sys

try:
    from src.prompt_manager import main
except ImportError:
    src_dir = Path(__file__).resolve().parent / "src"
    if str(src_dir) not in sys.path:
        sys.path.insert(0, str(src_dir))
    from prompt_manager import main

if __name__ == "__main__":
    main()
