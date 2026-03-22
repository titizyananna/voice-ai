
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from base_scraper import BaseBankScraper


class ACBABankScraper(BaseBankScraper):

    def __init__(self):
        super().__init__(
            bank_name="ACBA Bank",
            base_url="https://www.acba.am/hy",
        )

    def scrape_credits(self) -> list[dict]:
        pages = [
            ("Առանց գրավի սպառողական վարկեր",   "https://www.acba.am/hy/individuals/loans/consumer-credits/up-to-5-million"),
            ("Ուսման վարկեր",   "https://www.acba.am/hy/individuals/loans/consumer-credits/usman-varker"),
            ("Գրավով սպառողական վարկեր",  "https://www.acba.am/hy/individuals/loans/collateral-loans/deposit-secured"),
            ("Անշարժ գույքի գնման հիփօթեքային վարկեր",  "https://www.acba.am/hy/individuals/loans/mortgage/purchase-mortgage"),
            ("Անշարժ գույքի վերանորոգման հիփօթեքային վարկեր", "https://www.acba.am/hy/individuals/loans/renovative-loans/1579071546"),
            ("Բիզնես վարկեր","https://www.acba.am/hy/business/get-a-loan/Fixed-rate-loans"),
            ("էքսպրես բիզնես վարկեր","https://www.acba.am/hy/business/get-a-loan/Express-loans"),
            
        ]
        return self._scrape_pages(pages)

    def scrape_deposits(self) -> list[dict]:
        pages = [
            ("Դասական ավանդ", "https://www.acba.am/hy/individuals/save-and-invest/deposits/classic"),
            ("Կուտակվող ավանդ", "https://www.acba.am/hy/individuals/save-and-invest/deposits/accumulative"),
            ("Ընտանեկան ավանդ",  "https://www.acba.am/hy/individuals/save-and-invest/deposits/family"),
            ("Ավանդ երեխաների համար",  "https://www.acba.am/hy/individuals/save-and-invest/deposits/for-children"),
        ]
        return self._scrape_pages(pages)
    
    def scrape_branches(self) -> list[dict]:
        url = "https://www.acba.am/hy/about-bank/Branches-and-ATMs"
        soup = self.fetch_page(url)
        if not soup:
            return []

        self.remove_noise(soup)
        results = []

        for branch in soup.select(".fb_branch"):

            name_el = branch.select_one(".fb_branch__head__title")
            name = self.clean_text(name_el) if name_el else ""

            place_el = branch.select_one(".fb_branch__place")
            place = self.clean_text(place_el) if place_el else ""

            # 3 list items: [0] address, [1] working hours, [2] cash hours
            items = branch.select(".fb_branch__list__item")
            address       = self.clean_text(items[0]) if len(items) > 0 else ""
            working_hours = self.clean_text(items[1]) if len(items) > 1 else ""
            cash_hours    = self.clean_text(items[2]) if len(items) > 2 else ""

            if not name:
                continue

            results.append({
                "source_url": url,
                "name": name,
                "place": place,
                "address": address,
                "working_hours": working_hours,
                "cash_hours": cash_hours,
                "raw_text": f"{name}. {place}, {address}. {working_hours}",
            })

        print(f"  [ACBA Bank] branches: {len(results)} entries")
        return results

    def _scrape_pages(self, pages: list[tuple]) -> list[dict]:
        results = []
        for title, url in pages:
            print(f"  [ACBA Bank] Fetching: {title}")
            soup = self.fetch_page(url)
            if not soup:
                continue

            self.remove_noise(soup)
            table_text = self.extract_tables(soup)

            main = soup.select_one(
                "main, .main-content, .page-content, "
                "#content, article, .product-description"
            )
            prose = self.clean_text(main)[:3000] if main else ""

            if table_text and prose:
                details = f"{prose}\n\nRATE TABLE:\n{table_text}"[:4000]
            elif table_text:
                details = table_text[:4000]
            else:
                details = prose

            if len(details) < 50:
                print(f"  [ACBA Bank] Warning: very little content for {title}")
                continue

            results.append({
                "source_url": url,
                "title": title,
                "details": details,
            })

        return results

ACBABankScraper().run()