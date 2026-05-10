from __future__ import annotations

import asyncio
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

from app.db.session import create_all


async def main() -> None:
    await create_all()
    print("✓ Tables created (or already existed).")


if __name__ == "__main__":
    asyncio.run(main())
