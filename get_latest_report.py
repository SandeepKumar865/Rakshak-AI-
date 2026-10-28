"""
Rakshak AI — Terminal Report Viewer
Fetches and displays the structured summary of the latest call report directly in the terminal,
and automatically opens the PDF report.

Usage:
    py get_latest_report.py
    py get_latest_report.py --no-open
"""

import sys
import os
import json
import glob
from pathlib import Path

# Ensure UTF-8 printing on Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

BASE_DIR = Path(__file__).resolve().parent
REPORTS_DIR = BASE_DIR / "reports"


def get_latest_report():
    if not REPORTS_DIR.exists():
        print(f"[ERROR] Reports directory not found at: {REPORTS_DIR}")
        return

    json_files = list(REPORTS_DIR.glob("Data_*.json"))
    if not json_files:
        print("[ERROR] No report metadata files found in reports/")
        return

    # Find latest JSON by modification time
    latest_json = max(json_files, key=lambda f: f.stat().st_mtime)

    with open(latest_json, "r", encoding="utf-8") as f:
        data = json.load(f)

    report_id = data.get("report_id", "UNKNOWN")

    # Find matching PDF
    matching_pdfs = list(REPORTS_DIR.glob(f"Rakshak_Report_{report_id}*.pdf"))
    latest_pdf = matching_pdfs[0] if matching_pdfs else (REPORTS_DIR / "LATEST_REPORT.pdf")

    print("\n" + "=" * 65)
    print("        🛡️  RAKSHAK AI — LATEST INCIDENT REPORT  🛡️")
    print("=" * 65)
    print(f"  • Report ID         : {report_id}")
    print(f"  • Timestamp         : {data.get('started_at', 'N/A')}")
    print(f"  • Call SID          : {data.get('call_sid', 'N/A')}")
    print(f"  • Citizen Name      : {data.get('name', 'N/A')}")
    print(f"  • Language          : {data.get('language', 'hi').upper()}")
    print(f"  • Fraud Category    : {data.get('scenario', 'GENERAL_FRAUD')} ({data.get('scenario_label', '')})")
    print(f"  • Financial Loss    : ₹{data.get('financial_loss', 'Not specified')}")
    print(f"  • Incident Date     : {data.get('incident_date', 'Not specified')}")
    
    bank = data.get("bank_details", {})
    if bank and isinstance(bank, dict):
        bank_name = bank.get("bank_name")
        if bank_name:
            print(f"  • Bank Identified   : {bank_name}")

    print("-" * 65)
    print("  VERBAL INCIDENT STATEMENT:")
    print(f"  \"{data.get('story', 'No description recorded')}\"")
    
    details = data.get("details")
    if details:
        print("\n  ADDITIONAL DISCLOSURES:")
        print(f"  \"{details}\"")

    draft = data.get("formal_complaint_draft")
    if draft:
        print("-" * 65)
        print("  FORMAL COMPLAINT DRAFT (READY FOR CYBERCRIME.GOV.IN):")
        for line in draft.strip().split("\n"):
            print(f"    {line}")

    print("=" * 65)
    if latest_pdf.exists():
        print(f"  📄 PDF Document     : {latest_pdf.name}")
        print(f"  📁 Full Path        : {latest_pdf}")
        print("=" * 65)
        
        # Open PDF if not disabled
        if "--no-open" not in sys.argv:
            try:
                print("  Opening PDF report in default viewer...")
                os.startfile(str(latest_pdf))
            except Exception as e:
                print(f"  [Notice] Could not auto-open: {e}")
    else:
        print(f"  [Notice] PDF document not found for {report_id}")
    print()


if __name__ == "__main__":
    get_latest_report()
