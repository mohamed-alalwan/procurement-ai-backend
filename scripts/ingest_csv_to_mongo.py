import os
import csv
from pathlib import Path
from typing import Any, Dict, List, Optional
from datetime import datetime
from pymongo import MongoClient
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


def normalizeKey(key: str) -> str:
    return key.strip().lower().replace(" ", "_").replace("-", "_")


def parseUsDate(value: Any) -> Optional[datetime]:
    if value is None:
        return None

    s = str(value).strip()

    if not s:
        return None

    for fmt in ("%m/%d/%Y", "%m/%d/%y"):
        try:
            return datetime.strptime(s, fmt)
        except Exception:
            continue

    return None


def parseCurrency(value: Any) -> Optional[float]:
    if value is None:
        return None

    s = str(value).strip()

    if not s:
        return None

    s = s.replace("$", "").replace(",", "").strip()

    try:
        return float(s)
    except Exception:
        return None


def parseNumber(value: Any) -> Optional[float]:
    if value is None:
        return None

    s = str(value).strip()

    if not s:
        return None

    s2 = s.replace(",", "")

    try:
        return float(s2)
    except Exception:
        return None


def computeDateFields(doc: Dict[str, Any], dateField: str) -> None:
    dt = doc.get(dateField)

    if not isinstance(dt, datetime):
        return

    doc["calendar_year"] = dt.year

    doc["calendar_month"] = dt.month

    doc["calendar_quarter"] = int(((dt.month - 1) / 3) + 1)

    fiscalYearStart = dt.year if dt.month >= 7 else dt.year - 1

    doc["fiscal_year_start"] = fiscalYearStart

    fiscalMonth = ((dt.month - 7) % 12) + 1

    doc["fiscal_quarter"] = int(((fiscalMonth - 1) / 3) + 1)


def main() -> None:

    csvPath = os.getenv("DATASET_CSV_PATH", "").strip()

    if not csvPath:
        raise ValueError("Missing DATASET_CSV_PATH in .env")

    mongoUri = os.getenv("MONGODB_URI", "mongodb://localhost:27017")

    dbName = os.getenv("MONGODB_DB", "procurement")

    collectionName = os.getenv("MONGODB_COLLECTION", "purchases")

    csvFile = Path(csvPath)

    if not csvFile.exists():
        raise FileNotFoundError(f"CSV not found: {csvFile}")

    client = MongoClient(mongoUri)

    db = client[dbName]

    collection = db[collectionName]

    # Uncomment if you want a clean reload every time.
    # collection.delete_many({})

    insertedCount = 0

    batch: List[Dict[str, Any]] = []

    with csvFile.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)

        if not reader.fieldnames:
            raise ValueError("CSV has no headers")

        normalizedHeaders = [normalizeKey(h) for h in reader.fieldnames]

        for row in reader:
            doc: Dict[str, Any] = {}

            for originalKey, normalizedKey in zip(reader.fieldnames, normalizedHeaders):
                value = row.get(originalKey)

                parsedValue: Any = value

                if normalizedKey in ["creation_date", "purchase_date"]:
                    parsedValue = parseUsDate(value)

                elif normalizedKey in ["unit_price", "total_price"]:
                    parsedValue = parseCurrency(value)

                elif normalizedKey in ["quantity"]:
                    parsedValue = parseNumber(value)

                else:
                    if value is None:
                        parsedValue = None
                    else:
                        parsedValue = str(value).strip()

                        if parsedValue == "":
                            parsedValue = None

                doc[normalizedKey] = parsedValue

            computeDateFields(doc, "creation_date")

            batch.append(doc)

            if len(batch) >= 1000:
                collection.insert_many(batch)

                insertedCount += len(batch)

                batch = []

        if batch:
            collection.insert_many(batch)

            insertedCount += len(batch)

    # Helpful indexes for analytics queries.
    collection.create_index("creation_date")

    collection.create_index("calendar_year")

    collection.create_index("calendar_month")

    collection.create_index("calendar_quarter")

    collection.create_index("fiscal_year_start")

    collection.create_index("fiscal_quarter")

    collection.create_index("supplier_name")

    collection.create_index("department_name")

    print(f"Inserted: {insertedCount} documents into {dbName}.{collectionName}")


if __name__ == "__main__":
    main()
