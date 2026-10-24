"""Run established M8 real-browser journeys without overwriting historical M8 evidence."""

from pathlib import Path

import m8_browser

if __name__ == "__main__":
    m8_browser.OUT = (
        Path(__file__).resolve().parents[2] / "docs/evidence/marketplace-ai/regression"
    )
    m8_browser.main()
