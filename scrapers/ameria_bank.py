import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from base_scraper import BaseBankScraper

class AmeriabankScraper(BaseBankScraper):

    def __init__(self):
        super().__init__(
            bank_name="Ameriabank",
            base_url="https://ameriabank.am/",
        )

    def scrape_credits(self) -> list[dict]:
        pages = [
            ("Սպառողական վարկեր",  "https://ameriabank.am/loans/consumer-loans"),
            ("Հիփոթեքային վարկեր",       "https://ameriabank.am/personal/loans/mortgage-loans"),
            ("Ավտովարկեր",       "https://ameriabank.am/personal/loans/car-loans"),
            ("Բիզնես վարկեր",  "https://ameriabank.am/business/micro/loans"),
            ("Գրավով ապահովված վարկեր",  "https://ameriabank.am/loans/secured-loans"),
        ]
        return self._scrape_product_pages(pages, topic="credits")

    def scrape_deposits(self) -> list[dict]:
        pages = [

            ("Ամերիա ավանդ",              "https://ameriabank.am/personal/saving/deposits/ameria-deposit"),
            ("Ամերիա Մանկական ավանդ",     "https://ameriabank.am/personal/saving/deposits/kids-deposit"),
            ("Ամերիա Կուտակային ավանդ",   "https://ameriabank.am/personal/saving/deposits/cumulative-deposit"),
        ]
        return self._scrape_product_pages(pages, topic="deposits")

    
    def scrape_branches(self) -> list[dict]:
        url = "https://ameriabank.am/service-network"
        soup = self.fetch_page(url, force_playwright=True)
        if not soup:
            return []

        self.remove_noise(soup)
        results = []

        for branch in soup.select(".sidebar-item"):
            name_el    = branch.select_one(".sidebar-item__title")
            addr_el    = branch.select_one(".sidebar-item__location")
            phone_el   = branch.select_one(".sidebar-item__phone")
            tag_el     = branch.select_one(".sidebar-item__tag")

            name  = self.clean_text(name_el)  if name_el  else ""
            addr  = self.clean_text(addr_el)  if addr_el  else ""
            phone = self.clean_text(phone_el) if phone_el else ""
            tag   = self.clean_text(tag_el)   if tag_el   else ""

            if not name:
                continue

            results.append({
                "source_url": url,
                "name":         name,
                "address":      addr,
                "phone":        phone,
                "schedule":     tag,
                "raw_text":     f"{name}. {addr}. {phone}. {tag}",
            })

        print(f"  [Ameriabank] branches: {len(results)} entries")
        return results
    # def scrape_branches(self) -> list[dict]:
    #     """
    #     Ameriabank lists all branches on one page.
    #     We extract each branch block into a separate dict entry.
    #     """
    #     url = "https://ameriabank.am/service-network"
    #     soup = self.fetch_page(url)
    #     if not soup:
    #         print(f"  [Ameriabank] Could not fetch branches page")
    #         return []

    #     self.remove_noise(soup)
    #     results = []

    #     # Try structured branch cards first
    #     # Inspect ameriabank.am/en/about/branches and update this selector
    #     branch_cards = soup.select(".branch-item, .branch-card, .location-item, [class*='branch']")

    #     if branch_cards:
    #         for card in branch_cards:
    #             name_el  = card.select_one("h3, h4, .branch-name, .title, strong")
    #             addr_el  = card.select_one(".address, .branch-address, p")
    #             phone_el = card.select_one(".phone, a[href^='tel'], .tel")

    #             name  = self.clean_text(name_el)  if name_el  else ""
    #             addr  = self.clean_text(addr_el)  if addr_el  else ""
    #             phone = self.clean_text(phone_el) if phone_el else ""

    #             if not name and not addr:
    #                 continue

    #             results.append({
    #                 "source_url": url,
    #                 "name": name,
    #                 "address": addr,
    #                 "phone": phone,
    #                 "raw_text": self.clean_text(card)[:400],
    #             })
    #     else:
    #         # Fallback: scrape the whole page as one big text block
    #         main = soup.select_one("main, .main-content, #content, .page-content")
    #         if main:
    #             results.append({
    #                 "source_url": url,
    #                 "name": "All Ameriabank branches",
    #                 "address": "",
    #                 "phone": "",
    #                 "raw_text": self.clean_text(main)[:4000],
    #             })

    #     print(f"  [Ameriabank] branches: {len(results)} entries")
    #     return results

    # ------------------------------------------------------------------
    # SHARED HELPER
    # ------------------------------------------------------------------

    def _scrape_product_pages(self, pages: list[tuple], topic: str) -> list[dict]:
        """
        For each (title, url) pair, fetch the page and extract the main content.
        Also captures any rate tables present on the page.
        """
        results = []
        for title, url in pages:
            print(f"  [Ameriabank] Fetching {topic}: {title}")
            soup = self.fetch_page(url, force_playwright=True)
            if not soup:
                print(f"  [Ameriabank] Skipping {title} — could not fetch")
                continue

            self.remove_noise(soup)

            # Extract rate tables (most important — don't lose these)
            table_text = self.extract_tables(soup)

            # Extract main prose content
            main = soup.select_one(
                "main, .main-content, .page-content, "
                "#content, article, .product-detail"
            )
            if not main:
                main = soup.body

            prose = self.clean_text(main)[:3000] if main else ""

            # Combine prose + table, prefer table if both exist
            if table_text and prose:
                details = f"{prose}\n\nRATE TABLE:\n{table_text}"[:4000]
            elif table_text:
                details = table_text[:4000]
            else:
                details = prose

            if len(details) < 50:
                print(f"  [Ameriabank] Warning: very little content extracted for {title}")
                continue

            results.append({
                "source_url": url,
                "title": title,
                "details": details,
            })

        return results


scraper = AmeriabankScraper()
scraper.run()