"""
Validation script to test sample queries on procurement CSV data.
Ensures data is properly structured and queryable before ingestion.

Usage:
    python validate_csv_queries.py
"""

import os
import sys
import csv
from pathlib import Path
from typing import Any, Dict, List
from datetime import datetime
from collections import defaultdict
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


def normalizeKey(key: str) -> str:
    return key.strip().lower().replace(" ", "_").replace("-", "_")


def parseUsDate(value: Any) -> datetime | None:
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


def parseCurrency(value: Any) -> float | None:
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


def parseNumber(value: Any) -> float | None:
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


def getFiscalYear(dt: datetime) -> str:
    """Get fiscal year string (e.g., '2014-2015') - FY starts July 1"""
    if dt.month >= 7:
        return f"{dt.year}-{dt.year + 1}"
    else:
        return f"{dt.year - 1}-{dt.year}"


def getCalendarQuarter(dt: datetime) -> int:
    return int(((dt.month - 1) / 3) + 1)


def getFiscalQuarter(dt: datetime) -> int:
    """Fiscal quarter - July=Q1"""
    fiscalMonth = ((dt.month - 7) % 12) + 1
    return int(((fiscalMonth - 1) / 3) + 1)


def loadCsvData(csvPath: str) -> List[Dict[str, Any]]:
    """Load and parse CSV data"""
    csvFile = Path(csvPath)
    if not csvFile.exists():
        raise FileNotFoundError(f"CSV not found: {csvFile}")
    
    data = []
    
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
            
            # Add derived calendar/fiscal fields from creation_date for queries
            if doc.get("creation_date") and isinstance(doc["creation_date"], datetime):
                dt = doc["creation_date"]
                doc["calendar_year"] = dt.year
                doc["calendar_quarter"] = getCalendarQuarter(dt)
                doc["fiscal_quarter"] = getFiscalQuarter(dt)
                doc["calendar_month"] = dt.month
                # Note: fiscal_year already exists in CSV, no need to derive
            
            data.append(doc)
    
    return data


def printSection(title: str):
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80)


def formatCurrency(amount: float) -> str:
    if amount >= 1_000_000_000:
        return f"${amount / 1_000_000_000:.2f}B"
    elif amount >= 1_000_000:
        return f"${amount / 1_000_000:.2f}M"
    elif amount >= 1_000:
        return f"${amount / 1_000:.2f}K"
    else:
        return f"${amount:.2f}"


def test1_total_spend_by_fiscal_year(data: List[Dict]) -> None:
    """Q1: What is total spend in fiscal year YYYY-YYYY?"""
    printSection("Q1: Total Spend by Fiscal Year")
    
    spendByFY = defaultdict(float)
    
    for row in data:
        fy = row.get("fiscal_year")
        total = row.get("total_price")
        if fy and total is not None:
            spendByFY[fy] += total
    
    print(f"Found {len(spendByFY)} fiscal years:")
    for fy in sorted(spendByFY.keys()):
        print(f"  {fy}: {formatCurrency(spendByFY[fy])}")


def test2_top_department_by_fiscal_year(data: List[Dict], fiscalYear: str = "2014-2015") -> None:
    """Q2: Which department spent the most in fiscal year YYYY-YYYY?"""
    printSection(f"Q2: Top Department in FY {fiscalYear}")
    
    spendByDept = defaultdict(float)
    
    for row in data:
        if row.get("fiscal_year") == fiscalYear:
            dept = row.get("department_name") or "Unknown"
            total = row.get("total_price")
            if total is not None:
                spendByDept[dept] += total
    
    if not spendByDept:
        print(f"  No data found for FY {fiscalYear}")
        return
    
    sorted_depts = sorted(spendByDept.items(), key=lambda x: x[1], reverse=True)
    print(f"  Top 5 departments:")
    for i, (dept, spend) in enumerate(sorted_depts[:5], 1):
        print(f"    {i}. {dept}: {formatCurrency(spend)}")


def test3_top_suppliers_by_fiscal_year(data: List[Dict], fiscalYear: str = "2014-2015", topN: int = 10) -> None:
    """Q3: Who are the top N suppliers by spend in fiscal year YYYY-YYYY?"""
    printSection(f"Q3: Top {topN} Suppliers in FY {fiscalYear}")
    
    spendBySupplier = defaultdict(float)
    
    for row in data:
        if row.get("fiscal_year") == fiscalYear:
            supplier = row.get("supplier_name") or "Unknown"
            total = row.get("total_price")
            if total is not None:
                spendBySupplier[supplier] += total
    
    if not spendBySupplier:
        print(f"  No data found for FY {fiscalYear}")
        return
    
    sorted_suppliers = sorted(spendBySupplier.items(), key=lambda x: x[1], reverse=True)
    print(f"  Top {topN} suppliers:")
    for i, (supplier, spend) in enumerate(sorted_suppliers[:topN], 1):
        print(f"    {i}. {supplier}: {formatCurrency(spend)}")


def test4_spend_by_acquisition_method(data: List[Dict], fiscalYear: str = "2014-2015") -> None:
    """Q4: Spend breakdown by Acquisition Method"""
    printSection(f"Q4: Spend by Acquisition Method in FY {fiscalYear}")
    
    spendByMethod = defaultdict(float)
    
    for row in data:
        if row.get("fiscal_year") == fiscalYear:
            method = row.get("acquisition_method") or "(Blank/Unknown)"
            total = row.get("total_price")
            if total is not None:
                spendByMethod[method] += total
    
    if not spendByMethod:
        print(f"  No data found for FY {fiscalYear}")
        return
    
    sorted_methods = sorted(spendByMethod.items(), key=lambda x: x[1], reverse=True)
    total_spend = sum(spendByMethod.values())
    
    print(f"  Acquisition methods (Top method first):")
    for i, (method, spend) in enumerate(sorted_methods, 1):
        pct = (spend / total_spend * 100) if total_spend > 0 else 0
        print(f"    {i}. {method}: {formatCurrency(spend)} ({pct:.1f}%)")


def test5_order_count_by_period(data: List[Dict], fiscalYear: str = "2014-2015") -> None:
    """Q5: How many orders were created in a given period?"""
    printSection(f"Q5: Order Count in FY {fiscalYear}")
    
    # Use (department + PO number) for uniqueness
    uniqueOrders = set()
    
    for row in data:
        if row.get("fiscal_year") == fiscalYear:
            po = row.get("purchase_order_number")
            dept = row.get("department_name") or "Unknown"
            if po:
                uniqueOrders.add((dept, po))
    
    print(f"  Total unique orders: {len(uniqueOrders):,}")
    print(f"  (Using combination of Department + PO Number for uniqueness)")


def test6_highest_spend_quarter(data: List[Dict], calendarYear: int = 2014) -> None:
    """Q6: Which quarter had the highest total spend in a year?"""
    printSection(f"Q6: Highest Spend Quarter in {calendarYear}")
    
    spendByQuarter = defaultdict(float)
    
    for row in data:
        if row.get("calendar_year") == calendarYear:
            quarter = row.get("calendar_quarter")
            total = row.get("total_price")
            if quarter and total is not None:
                spendByQuarter[f"Q{quarter}"] += total
    
    if not spendByQuarter:
        print(f"  No data found for year {calendarYear}")
        return
    
    sorted_quarters = sorted(spendByQuarter.items(), key=lambda x: x[1], reverse=True)
    print(f"  Calendar quarters by spend:")
    for quarter, spend in sorted_quarters:
        print(f"    {quarter}: {formatCurrency(spend)}")
    
    # Also show fiscal quarters
    fiscalSpendByQuarter = defaultdict(float)
    fy = f"{calendarYear}-{calendarYear + 1}"
    for row in data:
        if row.get("fiscal_year") == fy:
            fq = row.get("fiscal_quarter")
            total = row.get("total_price")
            if fq and total is not None:
                fiscalSpendByQuarter[f"FQ{fq}"] += total
    
    if fiscalSpendByQuarter:
        print(f"\n  Fiscal quarters in FY {fy}:")
        fiscal_sorted = sorted(fiscalSpendByQuarter.items(), key=lambda x: x[1], reverse=True)
        for quarter, spend in fiscal_sorted:
            print(f"    {quarter}: {formatCurrency(spend)}")


def test7_it_vs_non_it_spend(data: List[Dict], fiscalYear: str = "2014-2015") -> None:
    """Q7: IT vs NON-IT spend split"""
    printSection(f"Q7: IT vs NON-IT Spend in FY {fiscalYear}")
    
    it_spend = 0.0
    non_it_spend = 0.0
    
    for row in data:
        if row.get("fiscal_year") == fiscalYear:
            acq_type = row.get("acquisition_type") or ""
            total = row.get("total_price")
            if total is not None:
                if acq_type.startswith("IT"):
                    it_spend += total
                elif acq_type.startswith("NON-IT"):
                    non_it_spend += total
    
    total = it_spend + non_it_spend
    if total > 0:
        print(f"  IT Spend:     {formatCurrency(it_spend)} ({it_spend/total*100:.1f}%)")
        print(f"  NON-IT Spend: {formatCurrency(non_it_spend)} ({non_it_spend/total*100:.1f}%)")
        print(f"  Total:        {formatCurrency(total)}")
    else:
        print(f"  No IT/NON-IT data found for FY {fiscalYear}")


def test8_qualified_supplier_spend(data: List[Dict], fiscalYear: str = "2014-2015") -> None:
    """Q8: How much spend went to SB/DVBE suppliers?"""
    printSection(f"Q8: Qualified Supplier Spend in FY {fiscalYear}")
    
    qualified_spend = 0.0
    other_spend = 0.0
    total_spend = 0.0
    
    for row in data:
        if row.get("fiscal_year") == fiscalYear:
            qualifications = row.get("supplier_qualifications") or ""
            total = row.get("total_price")
            if total is not None:
                total_spend += total
                # Check if supplier has ANY of the qualifications (no double counting)
                if "SB" in qualifications or "DVBE" in qualifications:
                    qualified_spend += total
                else:
                    other_spend += total
    
    if total_spend > 0:
        print(f"  Qualified Suppliers (SB/DVBE): {formatCurrency(qualified_spend)} ({qualified_spend/total_spend*100:.1f}%)")
        print(f"  Other Suppliers:                {formatCurrency(other_spend)} ({other_spend/total_spend*100:.1f}%)")
        print(f"  Total Spend:                    {formatCurrency(total_spend)}")
    else:
        print(f"  No data found for FY {fiscalYear}")


def test9_top_commodities(data: List[Dict], fiscalYear: str = "2014-2015", topN: int = 10) -> None:
    """Q9: Top commodities/categories by spend"""
    printSection(f"Q9: Top {topN} Commodities in FY {fiscalYear}")
    
    spendByCommodity = defaultdict(float)
    
    for row in data:
        if row.get("fiscal_year") == fiscalYear:
            # Use Commodity Title field
            commodity = row.get("commodity_title") or "Unknown"
            total = row.get("total_price")
            if total is not None:
                spendByCommodity[commodity] += total
    
    if not spendByCommodity:
        print(f"  No data found for FY {fiscalYear}")
        return
    
    sorted_commodities = sorted(spendByCommodity.items(), key=lambda x: x[1], reverse=True)
    print(f"  Top {topN} commodities:")
    for i, (commodity, spend) in enumerate(sorted_commodities[:topN], 1):
        print(f"    {i}. {commodity}: {formatCurrency(spend)}")


def test10_contract_vs_non_contract(data: List[Dict], fiscalYear: str = "2014-2015") -> None:
    """Q10: Contract vs non-contract spend (LPA usage)"""
    printSection(f"Q10: Contract vs Non-Contract Spend in FY {fiscalYear}")
    
    contract_spend = 0.0
    non_contract_spend = 0.0
    
    for row in data:
        if row.get("fiscal_year") == fiscalYear:
            lpa = row.get("lpa_number")
            total = row.get("total_price")
            if total is not None:
                if lpa and str(lpa).strip():
                    contract_spend += total
                else:
                    non_contract_spend += total
    
    total = contract_spend + non_contract_spend
    if total > 0:
        print(f"  Contract Spend (with LPA):     {formatCurrency(contract_spend)} ({contract_spend/total*100:.1f}%)")
        print(f"  Non-Contract Spend (no LPA):   {formatCurrency(non_contract_spend)} ({non_contract_spend/total*100:.1f}%)")
        print(f"  Total:                         {formatCurrency(total)}")
    else:
        print(f"  No data found for FY {fiscalYear}")


def main():
    # Get CSV path from environment
    csvPath = os.getenv("DATASET_CSV_PATH", "").strip()
    
    if not csvPath:
        raise ValueError("Missing DATASET_CSV_PATH in .env")
    
    print("\n" + "╔" + "═" * 78 + "╗")
    print("║" + " CSV DATA VALIDATION - SAMPLE Queries ".center(78) + "║")
    print("╚" + "═" * 78 + "╝")
    print(f"\nLoading data from: {csvPath}")
    
    data = loadCsvData(csvPath)
    print(f"Loaded {len(data):,} records")
    
    # Run all tests
    test1_total_spend_by_fiscal_year(data)
    test2_top_department_by_fiscal_year(data, "2014-2015")
    test3_top_suppliers_by_fiscal_year(data, "2014-2015", 10)
    test4_spend_by_acquisition_method(data, "2014-2015")
    test5_order_count_by_period(data, "2014-2015")
    test6_highest_spend_quarter(data, 2014)
    test7_it_vs_non_it_spend(data, "2014-2015")
    test8_qualified_supplier_spend(data, "2014-2015")
    test9_top_commodities(data, "2014-2015", 10)
    test10_contract_vs_non_contract(data, "2014-2015")
    
    print("\n" + "=" * 80)
    print("  VALIDATION COMPLETE")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    main()
