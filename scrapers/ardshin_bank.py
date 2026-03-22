import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from base_scraper import BaseBankScraper


class ArdshinbankScraper(BaseBankScraper):

    def __init__(self):
        super().__init__(
            bank_name="Ardshinbank",
            base_url="https://ardshinbank.am/?lang=hy",
        )

    def scrape_credits(self) -> list[dict]:
        pages = [
            ("Սպառողական վարկեր", "https://ardshinbank.am/for-you/loans-ardshinbank?lang=hy"),
            ("Հիփոթեքային վարկեր", "https://ardshinbank.am/for-you/mortgage?lang=hy"),
        ]
        return self._scrape_pages(pages)

    def scrape_deposits(self) -> list[dict]:
        pages = [
            ("Ավանդ",  "https://ardshinbank.am/for-you/avand?lang=hy"),
        ]
        return self._scrape_pages(pages)
    
    def scrape_branches(self) -> list[dict]:
        url = "https://ardshinbank.am/Information/branch-atm"
        soup = self.fetch_page(url, force_playwright=True)
        if not soup:
            return []

        self.remove_noise(soup)
        results = []

        for branch in soup.select(".col-lg-4"):
            name_el    = branch.select_one(".views-field-title")
            addr_el    = branch.select_one(".views-field-field-address")
            phone_el   = branch.select_one(".views-field-field-telephone")
            hours_el   = branch.select_one(".views-field-field-working-hours")

            name  = self.clean_text(name_el)  if name_el  else ""
            addr  = self.clean_text(addr_el)  if addr_el  else ""
            phone = self.clean_text(phone_el) if phone_el else ""
            hours = self.clean_text(hours_el) if hours_el else ""

            if not name:
                continue

            results.append({
                "source_url":    url,
                "name":          name,
                "address":       addr,
                "phone":         phone,
                "working_hours": hours,
                "raw_text":      f"{name}. {addr}. {phone}. {hours}",
            })

        print(f"  [Ardshinbank] branches: {len(results)} entries")
        return results
    
    def _scrape_pages(self, pages: list[tuple]) -> list[dict]:
        results = []
        for title, url in pages:
            print(f"  [Ardshinbank] Fetching: {title}")
            soup = self.fetch_page(url, force_playwright=True)
            if not soup:
                continue

            self.remove_noise(soup)

            # Extract all detail items — Ardshinbank uses tw-text-sm for loan details
            detail_items = soup.select(".tw-text-sm")
            if detail_items:
                details = " | ".join(
                    self.clean_text(el) for el in detail_items
                    if len(self.clean_text(el)) > 5
                )
            else:
                # Fallback to table or main content
                details = self.extract_tables(soup)
                if not details:
                    main = soup.select_one("main, .main-content, #content")
                    details = self.clean_text(main)[:3000] if main else ""

            if len(details) < 50:
                print(f"  [Ardshinbank] Warning: very little content for {title}")
                continue

            results.append({
                "source_url": url,
                "title": title,
                "details": details[:4000],
            })
        return results


ArdshinbankScraper().run()