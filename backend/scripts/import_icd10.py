import argparse
import asyncio
import csv
from pathlib import Path

from core_app.db.session import AsyncSessionLocal
from core_app.repositories.coding_repository import CodingRepository


async def import_icd10_codes(csv_path: Path) -> None:
    imported = 0
    skipped = 0
    async with AsyncSessionLocal() as session:
        repository = CodingRepository(session)
        try:
            with csv_path.open("r", encoding="utf-8") as handle:
                reader = csv.DictReader(handle)
                for row_num, row in enumerate(reader, start=2):
                    try:
                        code = (row.get("code") or "").strip()
                        short_description = (row.get("short_description") or row.get("description") or "").strip()
                        long_description = (row.get("long_description") or "").strip() or None
                        if not code or not short_description:
                            skipped += 1
                            continue
                        await repository.upsert_icd10(
                            code=code,
                            short_description=short_description,
                            long_description=long_description,
                        )
                        imported += 1
                    except Exception as e:
                        print(f"Error processing row {row_num}: {e}")
                        skipped += 1
                        continue
            await session.commit()
        except FileNotFoundError:
            print(f"Error: CSV file not found at {csv_path}")
            return
        except Exception as e:
            print(f"Error reading CSV file: {e}")
            return
    print(f"Imported {imported} ICD-10 rows from {csv_path} (skipped {skipped})")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Import ICD-10 codes from CSV.")
    parser.add_argument("csv_path", type=Path, help="Path to ICD-10 CSV file with code/short_description columns")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    asyncio.run(import_icd10_codes(args.csv_path))
