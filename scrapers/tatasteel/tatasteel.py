"""
Tata Steel Scraper for JobMiner.

This scraper extracts job listings from Tata Steel careers website.
"""

import sys
import os
from typing import List, Optional
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, StaleElementReferenceException
import time
import re
from datetime import datetime

# Add parent directory to path to import base_scraper
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
from base_scraper import BaseScraper, JobListing

class TataSteelScraper(BaseScraper):
    """
    Tata Steel job scraper using Selenium.
    """
    
    def __init__(self, delay: float = 3.0):
        """Initialize the Tata Steel scraper."""
        super().__init__(delay=delay)
        self.base_url = "https://tatasteel.ripplehire.com"
        self.jobs_list_url = f"{self.base_url}/candidate/?token=kYAz91uy1lFDi6FeSiRZ&lang=en&source=CAREERSITE#list"
        self.driver = None
    
    def _init_driver(self):
        """Initialize Selenium WebDriver."""
        if self.driver is None:
            options = webdriver.ChromeOptions()
            options.add_argument("--headless=new")
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--disable-blink-features=AutomationControlled")
            options.add_experimental_option("excludeSwitches", ["enable-automation"])
            options.add_argument("--log-level=3")  
            options.add_argument("--output=/dev/null") 
            options.add_experimental_option('useAutomationExtension', False)
            options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
            self.driver = webdriver.Chrome(options=options)
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        return self.driver
    
    def _close_driver(self):
        """Close Selenium WebDriver."""
        if self.driver:
            self.driver.quit()
            self.driver = None

    def get_job_urls(self, search_term: str = "", location: str = "", max_pages: int = 1) -> List[str]:
        """
        Get job URLs from Tata Steel job listings.
        """
        driver = self._init_driver()
        job_urls = []
        
        try:
            self.logger.info(f"Loading Tata Steel jobs page: {self.jobs_list_url}")
            driver.get(self.jobs_list_url)
            
            # Wait for job listings to load
            WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, ".job.list-arrow"))
            )
            
            time.sleep(self.delay)
            
            # Scroll to load all jobs
            self._scroll_page(driver)
            
            # Find all job cards
            job_cards = driver.find_elements(By.CSS_SELECTOR, ".job.list-arrow")
            self.logger.info(f"Found {len(job_cards)} job cards on page")
            
            for card in job_cards:
                try:
                    # Extract job detail link
                    job_link = card.find_element(By.CSS_SELECTOR, "a.job-title")
                    job_href = job_link.get_attribute("href")
                    
                    if job_href and "#detail/job/" in job_href:
                        # Fix URL formatting - use proper URL construction
                        job_url = f"{self.base_url}/candidate/{job_href}" if job_href.startswith('#') else job_href
                        job_urls.append(job_url)
                            
                except NoSuchElementException:
                    continue
                except Exception as e:
                    self.logger.warning(f"Error extracting job URL from card: {e}")
                    continue
            
        except TimeoutException:
            self.logger.error("Timeout waiting for job listings to load")
        except Exception as e:
            self.logger.error(f"Error getting job URLs: {e}")
        finally:
            self._close_driver()
        
        return job_urls

    def parse_job(self, job_url: str) -> Optional[JobListing]:
        """
        Parse a single job listing from Tata Steel.
        For SPA sites, we extract info without detailed navigation.
        """
        driver = self._init_driver()
        
        try:
            # Load the main page first
            driver.get(self.jobs_list_url)
            
            # Wait for job listings to load
            WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, ".job.list-arrow"))
            )
            
            time.sleep(self.delay)
            
            # Extract job ID from URL
            job_id_match = re.search(r'job/(\d+)', job_url)
            job_id = job_id_match.group(1) if job_id_match else None
            
            # Find all job cards and look for matching one
            job_cards = driver.find_elements(By.CSS_SELECTOR, ".job.list-arrow")
            
            for card in job_cards:
                try:
                    # Check if this card matches our job
                    job_link = card.find_element(By.CSS_SELECTOR, "a.job-title")
                    card_href = job_link.get_attribute("href")
                    
                    if job_id and job_id in card_href:
                        # Parse this card
                        job = self._parse_job_card_simple(card, job_url)
                        return job
                        
                except StaleElementReferenceException:
                    continue
                except Exception:
                    continue
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error parsing job {job_url}: {e}")
            return None
        finally:
            self._close_driver()

    def scrape_jobs(self, search_term: str = "", location: str = "", max_pages: int = 1) -> List[JobListing]:
        """
        Main method to scrape all jobs from Tata Steel portal.
        Uses a simple approach without navigation to avoid stale elements.
        """
        driver = self._init_driver()
        jobs = []
        
        try:
            self.logger.info(f"Loading Tata Steel jobs page: {self.jobs_list_url}")
            driver.get(self.jobs_list_url)
            
            # Wait for job listings to load
            WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, ".job.list-arrow"))
            )
            
            time.sleep(self.delay)
            
            # Scroll to load all jobs
            self._scroll_page(driver)
            
            # Find all job cards
            job_cards = driver.find_elements(By.CSS_SELECTOR, ".job.list-arrow")
            self.logger.info(f"Found {len(job_cards)} job cards on page")
            
            # Extract information from each card without navigation
            for i, card in enumerate(job_cards):
                try:
                    self.logger.info(f"Processing job {i+1}/{len(job_cards)}")
                    
                    job = self._parse_job_card_simple(card)
                    if job:
                        jobs.append(job)
                    
                    time.sleep(0.5)  # Small delay between processing jobs
                    
                except StaleElementReferenceException:
                    self.logger.warning(f"Stale element for job {i+1}, skipping...")
                    continue
                except Exception as e:
                    self.logger.error(f"Error processing job card {i+1}: {e}")
                    continue
            
        except TimeoutException:
            self.logger.error("Timeout waiting for job listings to load")
        except Exception as e:
            self.logger.error(f"Error during scraping: {e}")
        finally:
            self._close_driver()
        
        return jobs

    def _scroll_page(self, driver):
        """Scroll page to load all content."""
        try:
            last_height = driver.execute_script("return document.body.scrollHeight")
            for _ in range(3):
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(2)
                new_height = driver.execute_script("return document.body.scrollHeight")
                if new_height == last_height:
                    break
                last_height = new_height
        except Exception as e:
            self.logger.warning(f"Error during scrolling: {e}")

    def _parse_job_card_simple(self, card, job_url: Optional[str] = None) -> Optional[JobListing]:
        """
        Parse job information directly from the job card without navigation.
        This avoids stale element issues.
        """
        try:
            # Extract basic info from card
            title_elem = card.find_element(By.CSS_SELECTOR, "a.job-title")
            title = title_elem.text.strip()
            
            # Extract job URL from the card if not provided
            if not job_url:
                job_href = title_elem.get_attribute("href")
                if job_href:
                    # Fix URL formatting
                    if job_href.startswith('#'):
                        job_url = f"{self.base_url}/candidate/{job_href}"
                    else:
                        job_url = job_href
                else:
                    job_url = self.jobs_list_url
            
            # Extract location, experience, and openings from the card
            location = "Not specified"
            experience = "Not specified"
            openings = "Not specified"
            
            try:
                info_elems = card.find_elements(By.CSS_SELECTOR, ".list-job li")
                for elem in info_elems:
                    text = elem.text.strip()
                    if 'Years' in text:
                        experience = text
                    elif 'Opening' in text:
                        openings = text
                    elif any(city in text for city in ['Kolkata', 'Mumbai', 'Delhi', 'Chennai', 'Bangalore', 'Hyderabad', 'Pune', 'Jamshedpur']):
                        location = text
                    elif 'location-text' in elem.get_attribute('class'):
                        location = text
            except:
                pass
            
            # Build description from available info
            description = f"Title: {title}\nLocation: {location}\nExperience: {experience}\nOpenings: {openings}\n\nCompany: Tata Steel"
            
            # Create JobListing
            job = JobListing(
                title=title,
                company="Tata Steel",
                location=location,
                description=description,
                posted_date=self._get_current_date(),
                job_url=job_url,
                experience_level=experience
            )
            
            self.logger.info(f"Successfully parsed job: {title}")
            return job
            
        except StaleElementReferenceException:
            self.logger.warning("Stale element reference while parsing job card")
            return None
        except Exception as e:
            self.logger.error(f"Error parsing job card: {e}")
            return None

    def _get_current_date(self):
        """Get current date for posted_date field."""
        return datetime.now().strftime("%Y-%m-%d")

def main():
    """Test the scraper."""
    scraper = TataSteelScraper(delay=2.0)
    
    print("\nGetting full jobs...")
    jobs = scraper.scrape_jobs(max_pages=1)
    
    print(f"Found {len(jobs)} jobs")
    
    for job in jobs:
        print(f"\nTitle: {job.title}")
        print(f"Location: {job.location}")
        print(f"Experience: {job.experience_level}")
        print(f"URL: {job.job_url}")
        print("-" * 50)
    
    if jobs:
        scraper.save_to_json(jobs, "tatasteel_jobs.json")
        scraper.save_to_csv(jobs, "tatasteel_jobs.csv")
        print(f"\nSaved {len(jobs)} jobs to files")

if __name__ == "__main__":
    main()