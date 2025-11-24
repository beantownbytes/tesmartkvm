"""Allow running the CLI as a module: python -m tesmartkvm"""

from .cli import main

if __name__ == "__main__":
    import sys
    sys.exit(main())
