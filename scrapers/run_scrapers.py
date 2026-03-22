"""
Results saved to data/scraped/<bank_name>.json
To add a new bank later:
  1. Create scraper/<new_bank>.py subclassing BaseBankScraper
  2. Import it here and add to SCRAPERS list — nothing else changes
"""
import json
import os
import sys

from ameria_bank  import AmeriabankScraper
from ardshin_bank import ArdshinbankScraper
from acba_bank  import ACBABankScraper

SCRAPERS = [
    AmeriabankScraper,
    ArdshinbankScraper,
    ACBABankScraper,
    # Add new banks here, e.g.:
    # from scraper.evocabank import EvocabankScraper
    # EvocabankScraper,
]


def print_summary(path: str):
    """Print a quick summary of what was scraped."""
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    print(f"\n  Summary for {data['bank']}:")
    print(f"    Credits:  {len(data['credits'])} products")
    print(f"    Deposits: {len(data['deposits'])} products")
    print(f"    Branches: {len(data['branches'])} locations")
    # Warn if any section is empty
    for section in ["credits", "deposits", "branches"]:
        if len(data[section]) == 0:
            print(f"    WARNING: {section} is empty — check selectors or URL")


if __name__ == "__main__":
    results = {"success": [], "failed": []}

    for ScraperClass in SCRAPERS:
        scraper = ScraperClass()
        try:
            path = scraper.run()
            print_summary(path)
            results["success"].append(scraper.bank_name)
        except Exception as e:
            print(f"\n[ERROR] {scraper.bank_name} failed: {e}")
            results["failed"].append(scraper.bank_name)

    print("\n" + "="*50)
    print(f"DONE. Success: {results['success']}")
    if results["failed"]:
        print(f"FAILED: {results['failed']}")
        print("Check the error messages above and fix the selectors.")
    else:
        print("All banks scraped successfully!")
    print(f"Data saved in: data/scraped/")
