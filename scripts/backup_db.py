import sqlite3
import sys
from pathlib import Path
from datetime import datetime

LIVE = Path(r"F:\ContextKeep\data\contextkeep.db")
DEST_DIR = Path(r"F:\OneDrive\users\twitch\ContextKeep\backups")


def main():
    if not LIVE.exists():
        print(f"FAIL: live database not found: {LIVE}")
        return 1

    DEST_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y-%m-%d_%H%M")
    dest = DEST_DIR / f"contextkeep_{stamp}.db"

    src = sqlite3.connect(LIVE)
    live_count = src.execute("SELECT COUNT(*) FROM memories").fetchone()[0]
    out = sqlite3.connect(dest)
    src.backup(out)
    out.close()
    src.close()

    chk = sqlite3.connect(dest)
    integrity = chk.execute("PRAGMA integrity_check").fetchone()[0]
    bak_count = chk.execute("SELECT COUNT(*) FROM memories").fetchone()[0]
    chk.close()

    if integrity != "ok" or bak_count != live_count:
        print(f"FAIL: integrity={integrity} live={live_count} backup={bak_count}")
        return 1

    print(f"OK: {dest.name}  {bak_count} memories  {dest.stat().st_size} bytes")
    return 0


sys.exit(main())