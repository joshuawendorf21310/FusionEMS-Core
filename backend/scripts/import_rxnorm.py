import argparse
import asyncio
import csv
from pathlib import Path

from core_app.db.session import AsyncSessionLocal
from core_app.repositories.coding_repository import CodingRepository


async def import_rxnorm_codes(csv_path: Path) -> None:
    imported = 0
    skipped = 0
    async with AsyncSessionLocal() as session:
        repository = CodingRepository(session)
        try:
            with csv_path.open("r", encoding="utf-8") as handle:
                reader = csv.DictReader(handle)
                for row_num, row in enumerate(reader, start=2):
                    try:
                        rxcui = (row.get("rxcui") or "").strip()
                        name = (row.get("name") or "").strip()
                        tty = (row.get("tty") or "").strip() or None
                        if not rxcui or not name:
                            skipped += 1
                            continue
                        await repository.upsert_rxnorm(rxcui=rxcui, name=name, tty=tty)
                        imported += 1
                    except Exception as e:
                        print(f"Error processing row {row_num}: {e}")
                        await session.rollback()
                        skipped += 1
                        continue
            await session.commit()
        except FileNotFoundError:
            print(f"Error: CSV file not found at {csv_path}")
            return
        except Exception as e:
            print(f"Error reading CSV file: {e}")
            return
    print(f"Imported {imported} RxNorm rows from {csv_path} (skipped {skipped})")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Import RxNorm codes from CSV.")
    parser.add_argument("csv_path", type=Path, help="Path to RxNorm CSV file with rxcui/name/tty columns")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    asyncio.run(import_rxnorm_codes(args.csv_path))
