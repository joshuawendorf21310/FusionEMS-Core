import argparse
import asyncio
import csv
from pathlib import Path

from core_app.db.session import AsyncSessionLocal
from core_app.repositories.coding_repository import CodingRepository


async def import_icd10_codes(csv_path: Path) -> None:
    imported = 0
    async with AsyncSessionLocal() as session:
        repository = CodingRepository(session)
        with csv_path.open("r", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            for row in reader:
                code = (row.get("code") or "").strip()
                short_description = (row.get("short_description") or row.get("description") or "").strip()
                long_description = (row.get("long_description") or "").strip() or None
                if not code or not short_description:
                    continue
                await repository.upsert_icd10(
                    code=code,
                    short_description=short_description,
                    long_description=long_description,
                )
                imported += 1
        await session.commit()
    print(f"Imported {imported} ICD-10 rows from {csv_path}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Import ICD-10 codes from CSV.")
    parser.add_argument("csv_path", type=Path, help="Path to ICD-10 CSV file with code/short_description columns")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    asyncio.run(import_icd10_codes(args.csv_path))
