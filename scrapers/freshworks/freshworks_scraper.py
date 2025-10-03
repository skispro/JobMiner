"""
Freshworks (SmartRecruiters) scraper using requests + BeautifulSoup.

List page: https://careers.smartrecruiters.com/freshworks  (contains anchors to jobs.smartrecruiters.com)
Job detail pages are on jobs.smartrecruiters.com/...
"""

import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import time
import csv
import re

class FreshworksScraper:
    def __init__(self, base_list_url="https://careers.smartrecruiters.com/freshworks", delay=1.0):
        self.base_list_url = base_list_url
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (compatible; JobMinerBot/1.0; +https://example.com/bot)"
        })
        self.delay = delay

    def get_job_urls(self):
        """
        Get all job detail URLs by scraping the SmartRecruiters company page.
        Anchors typically point to jobs.smartrecruiters.com/... which are full URLs or relative.
        """
        r = self.session.get(self.base_list_url, timeout=15)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "lxml")
        urls = []
        for a in soup.find_all("a", href=True):
            href = a["href"]
            if "jobs.smartrecruiters.com" in href or "/freshworks/" in href:
                # normalize
                full = urljoin(self.base_list_url, href)
                if full not in urls:
                    urls.append(full)
        return urls

    def parse_job(self, job_url: str):
        try:
            r = self.session.get(job_url, timeout=12)
            r.raise_for_status()
            soup = BeautifulSoup(r.text, "lxml")
            # Title: usually h1
            title_tag = soup.find("h1")
            title = title_tag.get_text(strip=True) if title_tag else (soup.title.string.strip() if soup.title else "")

            # Try to find Job Description block
            # SmartRecruiters often includes a section labeled "Job Description" and the content beneath it
            main_text = soup.get_text("\n", strip=True)
            description = ""
            if re.search(r"Job\s*Description", main_text, re.I):
                parts = re.split(r"Job\s*Description", main_text, maxsplit=1, flags=re.I)
                description = parts[1].strip() if len(parts) > 1 else main_text
            else:
                # fallback: read main article/body
                container = soup.find("div", {"id": re.compile(r"job|content", re.I)}) or soup.find("article") or soup.body
                description = container.get_text("\n", strip=True) if container else main_text

            # try to extract location and posted date
            posted = None
            loc = None
            m = re.search(r"(Posted|Posted on|Date posted)[:\s\-]*([A-Za-z0-9\,\s\-\/]+)", main_text, re.I)
            if m:
                posted = m.group(2).strip()
            mloc = re.search(r"(Location|City)[:\s\-]*([A-Za-z0-9\,\-\s\/]+)", main_text, re.I)
            if mloc:
                loc = mloc.group(2).strip()

            return {
                "title": title,
                "company": "Freshworks",
                "location": loc,
                "posted_date": posted,
                "description": description,
                "job_url": job_url
            }
        except Exception as e:
            print(f"[FreshworksScraper] parse error for {job_url}: {e}")
            return None

    def scrape_jobs(self, limit=None):
        urls = self.get_job_urls()
        results = []
        for i, u in enumerate(urls):
            if limit and i >= limit:
                break
            time.sleep(self.delay)
            parsed = self.parse_job(u)
            if parsed:
                results.append(parsed)
        return results

    def save_csv(self, jobs, filename="freshworks_jobs.csv"):
        if not jobs:
            print("No jobs to save.")
            return
        keys = ["title","company","location","posted_date","job_url","description"]
        with open(filename, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=keys)
            w.writeheader()
            for j in jobs:
                w.writerow({k: j.get(k, "") for k in keys})

if __name__ == "__main__":
    s = FreshworksScraper()
    jobs = s.scrape_jobs(limit=50)
    print(f"Found {len(jobs)} jobs")
    s.save_csv(jobs, "freshworks_jobs.csv")