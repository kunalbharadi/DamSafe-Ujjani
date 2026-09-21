"""DamSafe foundation; no numerical engine is simulated by this package."""

from pathlib import Path

from dotenv import load_dotenv

# Local settings are optional; process/container variables take precedence.
load_dotenv(Path(__file__).resolve().parents[2] / ".env", override=False)
