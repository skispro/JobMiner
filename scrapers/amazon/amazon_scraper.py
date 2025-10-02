"""
AmazonScraper for JobMiner.

Scrapes Amazon jobs:
- base: https://www.amazon.jobs
- search: https://www.amazon.jobs/en/search?base_query=<query>&country=IND
- job pages follow pattern: /en/jobs/<id>/<slug>
"""
import sys
import os
from typing import List, Optional
from urllib.parse import urljoin, quote
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import re

# Add parent directory to path to import base_scraper
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
from base_scraper import BaseScraper, JobListing

class AmazonScraper(BaseScraper):
    def __init__(self, delay: float = 2.0):
        super().__init__(delay=delay)
        self.base_url = "https://www.amazon.jobs"
        # we'll format the search URL per query; we add country=IND when a location is India
        self.search_url_template = f"{self.base_url}/en/search?base_query={{query}}"
        self.driver = None

    def _init_driver(self):
        if self.driver is None:
            options = webdriver.ChromeOptions()
            options.add_argument("--headless=new")
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--disable-gpu")
            self.driver = webdriver.Chrome(options=options)
        return self.driver

    def _close_driver(self):
        if self.driver:
            self.driver.quit()
            self.driver = None

    def get_job_urls(self, search_term: str, location: str = "", max_pages: int = 1) -> List[str]:
        driver = self._init_driver()
        job_urls = []
        seen = set()
        # build search URL
        query = quote(search_term)
        url = self.search_url_template.format(query=query)
        if location:
            # prefer country param for India to localize results
            url += "&country=IND&loc_query=" + quote(location)

        try:
            driver.get(url)
            # wait for dynamic job tiles to load (Selenium will render JS)
            WebDriverWait(driver, 12).until(
                EC.presence_of_all_elements_located((By.TAG_NAME, "a"))
            )

            pages_scraped = 0
            while pages_scraped < max_pages:
                # take any anchor linking to '/en/jobs/<id>'
                anchors = driver.find_elements(By.XPATH, "//a[contains(@href, '/en/jobs/')]")
                for a in anchors:
                    href = a.get_attribute("href")
                    if not href:
                        continue
                    # normalize (strip query params)
                    href_norm = href.split("?")[0].split("#")[0]
                    if href_norm not in seen and "/en/jobs/" in href_norm:
                        seen.add(href_norm)
                        job_urls.append(href_norm)
                pages_scraped += 1

                # try pagination: look for Next or page param
                if pages_scraped < max_pages:
                    try:
                        # Amazon.jobs uses a "Next" button sometimes
                        next_button = driver.find_element(By.XPATH, "//a[contains(., 'Next') or contains(@aria-label,'Next') or contains(@class,'next')]")
                        if next_button:
                            driver.execute_script("arguments[0].scrollIntoView(true);", next_button)
                            next_button.click()
                            time.sleep(self.delay)
                        else:
                            break
                    except Exception:
                        # Try URL-based pagination (if there is page= param)
                        try:
                            # attempt to increment page param if present
                            current = driver.current_url
                            # if there is a 'page' param, increment it; otherwise break
                            if "page=" in current:
                                m = re.search(r"page=(\d+)", current)
                                if m:
                                    page_no = int(m.group(1)) + 1
                                    next_url = re.sub(r"page=\d+", f"page={page_no}", current)
                                    driver.get(next_url)
                                    time.sleep(self.delay)
                                else:
                                    break
                            else:
                                break
                        except:
                            break

        except Exception as e:
            self.logger.error(f"Error getting Amazon job URLs: {e}")

        return job_urls

    def parse_job(self, job_url: str) -> Optional[JobListing]:
        driver = self._init_driver()
        try:
            driver.get(job_url)
            WebDriverWait(driver, 10).until(
                EC.presence_of_all_elements_located((By.TAG_NAME, "body"))
            )

            # Title: try common heading tags
            title = None
            for xp in ["//h1", "//h2", "//h3", "//*[contains(@class,'job-title')]", "//*[contains(@class,'JobTitle')]"]:
                try:
                    el = driver.find_element(By.XPATH, xp)
                    if el and el.text.strip():
                        title = el.text.strip()
                        break
                except:
                    continue

            # posted_date: look for "Job ID" block or posted/posted on
            posted_date = None
            location = None
            description = None

            page_text = driver.find_element(By.TAG_NAME, "body").text

            # attempt to extract Posted/Date/Locations
            m = re.search(r"(Posted\s*(On)?:?\s*)([A-Za-z0-9,\s\-]+)", page_text, re.IGNORECASE)
            if m:
                posted_date = m.group(3).strip()

            # location lines often include city names; use Amazon's labels if present
            m_loc = re.search(r"(Locations?:\s*)([A-Za-z0-9,.\-\s]+)\n", page_text, re.IGNORECASE)
            if m_loc:
                location = m_loc.group(2).strip()

            # Description container: Amazon job pages usually have a job description div
            for sel in [
                "//div[@id='job-content']",
                "//div[contains(@class,'job-description') or contains(@class,'jobContent')]",
                "//section[contains(@class,'description')]",
                "//div[contains(@id,'job-')]"
            ]:
                try:
                    el = driver.find_element(By.XPATH, sel)
                    text = el.text.strip()
                    if text:
                        description = text
                        break
                except:
                    continue

            if not description:
                # fallback: use a chunk of full page text
                description = page_text[:10000]

            # experience/skills: look for bullets or "Basic Qualifications / Preferred Qualifications"
            experience_level = None
            try:
                bullets = driver.find_elements(By.XPATH, "//*[contains(translate(text(),'BASIC QUALIFICATIONS','basic qualifications'),'basic qualifications')]/following::ul[1]/li")
                if bullets:
                    experience_level = "; ".join([b.text.strip() for b in bullets if b.text.strip()])
            except:
                pass

            job = JobListing(
                title=title or "Unknown Title",
                company="Amazon",
                location=location or "Not specified",
                description=description,
                posted_date=posted_date,
                job_url=job_url,
                experience_level=experience_level
            )
            return job

        except Exception as e:
            self.logger.error(f"Error parsing Amazon job {job_url}: {e}")
            return None

    def scrape_jobs(self, search_term: str, location: str = "", max_pages: int = 1) -> List[JobListing]:
        try:
            jobs = super().scrape_jobs(search_term, location, max_pages)
            return jobs
        finally:
            self._close_driver()


def main():
    scraper = AmazonScraper(delay=2.0)
    jobs = scraper.scrape_jobs(search_term="software engineer", location="India", max_pages=1)
    print(f"Found {len(jobs)} Amazon jobs.")
    if jobs:
        scraper.save_to_json(jobs, "amazon_jobs.json")
        scraper.save_to_csv(jobs, "amazon_jobs.csv")


if __name__ == "__main__":
    main()