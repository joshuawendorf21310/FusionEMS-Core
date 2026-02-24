import argparse
import asyncio
import csv
from pathlib import Path

from core_app.db.session import AsyncSessionLocal
from core_app.repositories.coding_repository import CodingRepository


async def import_rxnorm_codes(csv_path: Path) -> None:
    imported = 0
    async with AsyncSessionLocal() as session:
        repository = CodingRepository(session)
        with csv_path.open("r", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            for row in reader:
                rxcui = (row.get("rxcui") or "").strip()
                name = (row.get("name") or "").strip()
                tty = (row.get("tty") or "").strip() or None
                if not rxcui or not name:
                    continue
                await repository.upsert_rxnorm(rxcui=rxcui, name=name, tty=tty)
                imported += 1
        await session.commit()
    print(f"Imported {imported} RxNorm rows from {csv_path}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Import RxNorm codes from CSV.")
    parser.add_argument("csv_path", type=Path, help="Path to RxNorm CSV file with rxcui/name/tty columns")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    asyncio.run(import_rxnorm_codes(args.csv_path))
