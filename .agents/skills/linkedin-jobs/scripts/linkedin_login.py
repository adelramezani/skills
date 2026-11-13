"""Open a persistent, headed browser profile so the user can sign in to LinkedIn once.

    python scripts/linkedin_login.py [--config path]

Sign in by hand (2FA/CAPTCHA included), then close the window. The session is kept in
`profile_dir` and reused by linkedin_search.py. No credentials are read or stored here.
If using a non-bundled browser (browser_path), fully close that browser first.
"""
from __future__ import annotations

import argparse
from pathlib import Path

from li_config import load_config
from playwright.sync_api import sync_playwright


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config")
    cfg = load_config(ap.parse_args().config)
    profile = Path(cfg["profile_dir"])
    profile.mkdir(parents=True, exist_ok=True)
    kwargs = {"executable_path": cfg["browser_path"]} if cfg["browser_path"] else {}
    with sync_playwright() as p:
        ctx = p.chromium.launch_persistent_context(str(profile), headless=False,
                                                   viewport={"width": 1280, "height": 900}, **kwargs)
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        page.goto("https://www.linkedin.com/login")
        print(f"Profile: {profile}\nSign in, then close the browser window.")
        page.wait_for_event("close", timeout=0)
        ctx.close()


if __name__ == "__main__":
    main()
