import os
import json
import time
import requests
from abc import ABC, abstractmethod
from bs4 import BeautifulSoup
from datetime import datetime

class BaseBankScraper(ABC):
    def __init__(self, bank_name: str, base_url: str, output_dir: str = "data/scraped"):
        self.bank_name = bank_name
        self.base_url = base_url
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
 
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            "Accept-Language": "en-US,en;q=0.9,hy;q=0.8",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        })
 
 
    def fetch_page(self, url: str, force_playwright: bool = False) -> BeautifulSoup | None:
        """
        Fetch a page and return BeautifulSoup.
        Auto-switches to Playwright if the page appears JS-rendered.
        """
        if not force_playwright:
            soup = self._fetch_with_requests(url)
            if soup and self._has_real_content(soup):
                return soup
            print(f"  [{self.bank_name}] Looks JS-rendered, switching to Playwright: {url}")
 
        return self._fetch_with_playwright(url)
 
    def _fetch_with_requests(self, url: str, retries: int = 3) -> BeautifulSoup | None:
        for attempt in range(retries):
            try:
                time.sleep(1.5)  # polite delay between requests
                resp = self.session.get(url, timeout=20)
                resp.raise_for_status()
                return BeautifulSoup(resp.text, "html.parser")
            except requests.RequestException as e:
                print(f"  [{self.bank_name}] Attempt {attempt+1} failed for {url}: {e}")
                time.sleep(2 ** attempt)
        return None
 
    def _fetch_with_playwright(self, url: str) -> BeautifulSoup | None:
        """
        Headless Chromium browser for JS-heavy pages.
        Install: pip install playwright && playwright install chromium
        """
        try:
            from playwright.sync_api import sync_playwright
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()
                page.set_extra_http_headers({"Accept-Language": "en-US,en;q=0.9"})
                page.goto(url, wait_until="networkidle", timeout=30000)
                time.sleep(2)
                html = page.content()
                browser.close()
                return BeautifulSoup(html, "html.parser")
        except ImportError:
            print("  Playwright not installed. Run: pip install playwright && playwright install chromium")
            return None
        except Exception as e:
            print(f"  [{self.bank_name}] Playwright failed for {url}: {e}")
            return None
 
    def _has_real_content(self, soup: BeautifulSoup) -> bool:
        """Returns False if the page is a JS skeleton with almost no visible text."""
        return len(soup.get_text(separator=" ", strip=True)) > 300
 
    
    def clean_text(self, element) -> str:
        """Strip HTML tags and collapse whitespace."""
        if element is None:
            return ""
        text = element.get_text(separator=" ") if hasattr(element, "get_text") else str(element)
        return " ".join(text.split()).strip()
 
    def remove_noise(self, soup: BeautifulSoup) -> BeautifulSoup:
        """Remove nav, footer, scripts, cookie banners."""
        for tag in soup.select(
            "nav, footer, header, script, style, noscript, "
            ".breadcrumb, .cookie-banner, .popup, .modal, "
            "[class*='cookie'], [class*='banner'], [id*='cookie']"
        ):
            tag.decompose()
        return soup
 
    def extract_tables(self, soup: BeautifulSoup) -> str:
        """Convert HTML rate tables to readable pipe-separated text."""
        result = []
        for table in soup.find_all("table"):
            rows = []
            for tr in table.find_all("tr"):
                cells = [self.clean_text(td) for td in tr.find_all(["td", "th"])]
                cells = [c for c in cells if c]
                if cells:
                    rows.append(" | ".join(cells))
            if rows:
                result.append("\n".join(rows))
        return "\n\n".join(result)
 
 
    @abstractmethod
    def scrape_credits(self) -> list[dict]:
        pass
 
    @abstractmethod
    def scrape_deposits(self) -> list[dict]:
        pass
 
    @abstractmethod
    def scrape_branches(self) -> list[dict]:
        pass
 
    def scrape_all(self) -> dict:
        print(f"\n[{self.bank_name}] Starting scrape...")
        data = {
            "bank": self.bank_name,
            "scraped_at": datetime.utcnow().isoformat(),
            "credits": self.scrape_credits(),
            "deposits": self.scrape_deposits(),
            "branches": self.scrape_branches(),
        }
        print(
            f"[{self.bank_name}] Done — "
            f"{len(data['credits'])} credits, "
            f"{len(data['deposits'])} deposits, "
            f"{len(data['branches'])} branches"
        )
        return data
 
    def save(self, data: dict) -> str:
        filename = f"{self.bank_name.lower().replace(' ', '_')}.json"
        path = os.path.join(self.output_dir, filename)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"[{self.bank_name}] Saved → {path}")
        return path
 
    def run(self):
        data = self.scrape_all()
        return self.save(data)
 