"""
TechMahindraScraper for JobMiner.

Targets: https://careers.techmahindra.com/  — job list contains links like JobDetails.aspx?JobCode=...
"""
import sys
import os
import re
import time
from typing import List, Optional
from urllib.parse import urljoin

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# Add parent directory to path to import base_scraper
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
from base_scraper import BaseScraper, JobListing


class TechMahindraScraper(BaseScraper):
    """
    Scraper for Tech Mahindra careers site.
    Main page: https://careers.techmahindra.com/
    Job detail pages look like: https://careers.techmahindra.com/JobDetails.aspx?JobCode=...
    """
    def __init__(self, delay: float = 2.0):
        super().__init__(delay=delay)
        self.base_url = "https://careers.techmahindra.com"
        self.search_url = self.base_url
        self.driver = None

    def _init_driver(self):
        if self.driver is None:
            options = webdriver.ChromeOptions()
            options.add_argument("--headless=new")
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            self.driver = webdriver.Chrome(options=options)
        return self.driver

    def _close_driver(self):
        if self.driver:
            self.driver.quit()
            self.driver = None

    def get_job_urls(self, search_term: str, location: str = "", max_pages: int = 1) -> List[str]:
        """
        Collect job detail links that include 'JobDetails.aspx' on TechM career page.
        """
        driver = self._init_driver()
        job_urls = []
        try:
            driver.get(self.search_url)
            # Wait for some job-list content to load
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.XPATH, "//*[contains(text(),'Recent Jobs') or contains(text(),'Job Description')]"))
            )
            time.sleep(0.5)

            anchors = driver.find_elements(By.CSS_SELECTOR, "a[href*='JobDetails.aspx'], a[href*='JobDetails.aspx?']")
            for a in anchors:
                try:
                    href = a.get_attribute("href")
                    if href:
                        full = urljoin(self.base_url, href)
                        if full not in job_urls:
                            job_urls.append(full)
                except Exception:
                    continue

            # If no anchors found, try clickable elements which open detail pages (fallback)
            if not job_urls:
                # find Apply/Shortlist buttons and try to find nearest <a> ancestor or click to fetch resulting URL
                buttons = driver.find_elements(By.XPATH, "//*[contains(text(),'Apply/Shortlist') or contains(text(),'Apply') or contains(text(),'View Job')]")
                for b in buttons:
                    try:
                        a = b.find_element(By.XPATH, ".//ancestor::a[1]")
                        href = a.get_attribute("href")
                        if href:
                            full = urljoin(self.base_url, href)
                            if full not in job_urls:
                                job_urls.append(full)
                    except:
                        continue

        except Exception as e:
            self.logger.error(f"TechM get_job_urls error: {e}")

        return job_urls[:200]  # keep sane limit

    def parse_job(self, job_url: str) -> Optional[JobListing]:
        """
        Parse Tech Mahindra JobDetails.aspx pages for structured fields.
        Uses page text + regex to extract Post Date, Location, Skills, Reference No.
        """
        driver = self._init_driver()
        try:
            driver.get(job_url)
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            time.sleep(0.3)

            # Title: try headings first
            title = None
            for sel in ["h1", "h2", "h3", "div#JobDescription h3", "div.job-title"]:
                try:
                    el = driver.find_element(By.CSS_SELECTOR, sel)
                    if el and el.text.strip():
                        title = el.text.strip()
                        break
                except:
                    continue
            if not title:
                title = driver.title.strip() or "Tech Mahindra Job"

            # Grab visible job content
            try:
                container = driver.find_element(By.CSS_SELECTOR, "div#main, div#content, div.job-description, body")
                page_text = container.text.strip()
            except:
                page_text = driver.find_element(By.TAG_NAME, "body").text.strip()

            # Regex parse some fields
            posted_date = None
            location = None
            experience = None
            ref_no = None

            m = re.search(r"Job\s*Post\s*Date\s*[:\-]\s*([0-9]{1,2}/[0-9]{1,2}/[0-9]{2,4})", page_text, re.I)
            if m:
                posted_date = m.group(1).strip()
            mloc = re.search(r"Location\s*[:\-]\s*([A-Z0-9a-z\.,\-\s/\[\]]{2,120})", page_text, re.I)
            if mloc:
                location = mloc.group(1).strip()
            mref = re.search(r"Job\s*Reference\s*No\s*[:\-]\s*([0-9A-Za-z\-]+)", page_text, re.I)
            if mref:
                ref_no = mref.group(1).strip()

            # Experience or skill lines as fallback
            mexp = re.search(r"Total\s*Experience\s*[:\-]\s*([0-9\.\-\s+years]*)", page_text, re.I)
            if mexp:
                experience = mexp.group(1).strip()

            job = JobListing(
                title=title,
                company="Tech Mahindra",
                location=location,
                description=page_text,
                posted_date=posted_date,
                job_url=job_url,
                experience_level=experience or ref_no
            )
            return job

        except Exception as e:
            self.logger.error(f"TechM parse_job error for {job_url}: {e}")
            return None

    def scrape_jobs(self, search_term: str, location: str = "", max_pages: int = 1) -> List[JobListing]:
        try:
            jobs = super().scrape_jobs(search_term, location, max_pages)
            return jobs
        finally:
            self._close_driver()


def main():
    s = TechMahindraScraper(delay=1.0)
    jobs = s.scrape_jobs(search_term="engineer", location="India", max_pages=1)
    print(f"Found {len(jobs)} jobs")
    if jobs:
        s.save_to_json(jobs, "techmahindra_jobs.json")
        s.save_to_csv(jobs, "techmahindra_jobs.csv")


if __name__ == "__main__":
    main()