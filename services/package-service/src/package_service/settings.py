import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


def secret(name: str) -> str | None:
    """
    Return the secret `name`. If `<name>_FILE` is set, read the secret 
    from that file. Otherwise read `<name>`.
    """
    path = os.environ.get(f"{name}_FILE")
    if path:
        try:
            return Path(path).read_text().strip()
        except OSError as e:
            raise RuntimeError(f"Cannot read {name}_FILE ({path}): {e.strerror}.") from None
    return os.environ.get(name)