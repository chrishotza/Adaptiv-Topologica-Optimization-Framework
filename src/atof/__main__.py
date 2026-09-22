"""Allow ATOF to run as `python -m atof`."""

from .cli import main


if __name__ == "__main__":
    raise SystemExit(main())
