"""
Wipro Job Scraper for JobMiner.

This scraper extracts job listings from Wipro careers website.
"""

import sys
import os
from typing import List, Optional
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import time
import re
from datetime import datetime

# Add parent directory to path to import base_scraper
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
from base_scraper import BaseScraper, JobListing

class WiproScraper(BaseScraper):
    """
    Wipro job scraper using Selenium.
    """
    
    def __init__(self, delay: float = 3.0):
        """Initialize the Wipro scraper."""
        super().__init__(delay=delay)
        self.base_url = "https://careers.wipro.com"
        self.search_url = f"{self.base_url}/search?searchResultView=LIST"
        self.driver = None
    
    def _init_driver(self):
        """Initialize Selenium WebDriver with suppressed logging."""
        if self.driver is None:
            options = webdriver.ChromeOptions()
            options.add_argument("--headless=new")
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--disable-blink-features=AutomationControlled")
            options.add_argument("--disable-logging")
            options.add_argument("--log-level=3")
            options.add_experimental_option("excludeSwitches", ["enable-automation", "enable-logging"])
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

    def get_job_urls(self, search_term: str = "", location: str = "", max_pages: int = 10) -> List[str]:
        """
        Get job URLs from Wipro search results with pagination.
        Stops when no jobs are found on a page.
        """
        driver = self._init_driver()
        job_urls = []
        current_page = 1
        
        try:
            while current_page <= max_pages:
                page_url = f"{self.search_url}&pageNumber={current_page}"
                self.logger.info(f"Loading Wipro jobs page {current_page}: {page_url}")
                driver.get(page_url)
                
                # Wait for job listings to load
                try:
                    WebDriverWait(driver, 15).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, '[data-testid="jobCard"]'))
                    )
                except TimeoutException:
                    self.logger.info(f"No jobs found on page {current_page}, stopping pagination.")
                    break
                
                time.sleep(self.delay)
                
                # Scroll to load all jobs
                self._scroll_page(driver)
                
                # Find all job cards
                job_cards = driver.find_elements(By.CSS_SELECTOR, '[data-testid="jobCard"]')
                
                if not job_cards:
                    self.logger.info(f"No job cards found on page {current_page}, stopping pagination.")
                    break
                
                self.logger.info(f"Found {len(job_cards)} job cards on page {current_page}")
                
                page_job_count = 0
                for card in job_cards:
                    try:
                        # Extract job link
                        job_link = card.find_element(By.CSS_SELECTOR, 'a.jobCardTitle')
                        job_href = job_link.get_attribute("href")
                        
                        if job_href:
                            job_url = f"{self.base_url}{job_href}" if job_href.startswith('/') else job_href
                            job_urls.append(job_url)
                            page_job_count += 1
                            
                    except NoSuchElementException:
                        continue
                    except Exception as e:
                        self.logger.warning(f"Error extracting job URL from card: {e}")
                        continue
                
                self.logger.info(f"Extracted {page_job_count} job URLs from page {current_page}")
                
                # Stop if we got fewer than 10 jobs (likely last page)
                if len(job_cards) < 10:
                    self.logger.info(f"Only {len(job_cards)} jobs found on page {current_page}, likely last page. Stopping.")
                    break
                
                current_page += 1
                time.sleep(self.delay)  # Delay between page requests
            
        except Exception as e:
            self.logger.error(f"Error getting job URLs: {e}")
        
        return job_urls

    def parse_job(self, job_url: str) -> Optional[JobListing]:
        """
        Parse a single job listing from Wipro.
        """
        driver = self._init_driver()
        
        try:
            self.logger.info(f"Parsing job: {job_url}")
            driver.get(job_url)
            
            # Wait for job details to load
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            
            time.sleep(self.delay)
            
            # Extract all text content first
            page_text = driver.find_element(By.TAG_NAME, "body").text
            
            # Extract job title from URL or page
            title = self._extract_title(driver, page_text, job_url)
            
            # Extract location
            location = self._extract_location(page_text)
            
            # Extract posting date
            posting_date = self._extract_posting_date(page_text)
            
            # Extract experience level
            experience = self._extract_experience(page_text)
            
            # Extract job ID
            job_id = self._extract_job_id(page_text, job_url)
            
            # Extract job description
            description = self._extract_description(page_text)
            
            # Build comprehensive description
            full_description = self._build_full_description(
                title, location, experience, posting_date, 
                job_id, description, page_text
            )
            
            job = JobListing(
                title=title,
                company="Wipro",
                location=location,
                description=full_description,
                posted_date=posting_date,
                job_url=job_url,
                experience_level=experience
            )
            
            self.logger.info(f"Successfully parsed job: {title}")
            return job
            
        except Exception as e:
            self.logger.error(f"Error parsing job {job_url}: {e}")
            return None
        finally:
            self._close_driver()

    def _extract_title(self, driver, page_text: str, job_url: str) -> str:
        """Extract job title from page text or URL."""
        try:
            # Try to get title from h1 tag first
            title_elem = driver.find_element(By.TAG_NAME, "h1")
            title = title_elem.text.strip()
            if title and len(title) > 0:
                return title
        except:
            pass
        
        # Try to extract from URL
        try:
            # URL pattern: /job/Job-Title-Here/12345-en_US
            url_match = re.search(r'/job/([^/]+)/', job_url)
            if url_match:
                title_from_url = url_match.group(1).replace('-', ' ').title()
                return title_from_url
        except:
            pass
        
        # Try to find in page text
        try:
            # Look for common title patterns in text
            lines = page_text.split('\n')
            for line in lines:
                line = line.strip()
                if len(line) > 10 and len(line) < 100:  # Reasonable title length
                    if any(keyword in line.lower() for keyword in ['consultant', 'engineer', 'manager', 'analyst', 'developer']):
                        return line
        except:
            pass
            
        return "Title not found"

    def _extract_location(self, page_text: str) -> str:
        """Extract job location from page text."""
        try:
            # Common Indian locations
            locations = [
                'Bangalore', 'Bengaluru', 'Pune', 'Hyderabad', 'Chennai', 'Mumbai', 
                'Delhi', 'Gurgaon', 'Gurugram', 'Noida', 'Kolkata', 'Ahmedabad',
                'Coimbatore', 'Kochi', 'Trivandrum', 'Jaipur', 'Lucknow', 'Chandigarh'
            ]
            
            for location in locations:
                if location in page_text:
                    return location
                    
            # Look for location patterns
            location_patterns = [
                r'Location:\s*([^\n]+)',
                r'Location\s*([^\n]+)',
                r'Primary Location:\s*([^\n]+)'
            ]
            
            for pattern in location_patterns:
                match = re.search(pattern, page_text, re.IGNORECASE)
                if match:
                    location = match.group(1).strip()
                    if location:
                        return location
                        
        except:
            pass
        return "Location not specified"

    def _extract_posting_date(self, page_text: str) -> str:
        """Extract posting date from page text."""
        try:
            # Look for date patterns
            date_patterns = [
                r'Posting Start Date:\s*(\d{1,2}/\d{1,2}/\d{2,4})',
                r'Posting Start Date\s*(\d{1,2}/\d{1,2}/\d{2,4})',
                r'(\d{1,2}/\d{1,2}/\d{2,4})'
            ]
            
            for pattern in date_patterns:
                match = re.search(pattern, page_text)
                if match:
                    return match.group(1)
                    
        except:
            pass
        return self._get_current_date()

    def _extract_experience(self, page_text: str) -> str:
        """Extract experience requirements from page text."""
        try:
            # Look for experience patterns
            exp_patterns = [
                r'Experience:\s*([^\n]+)',
                r'(\d+\s*-\s*\d+\s*Years?)',
                r'(\d+\s*Years?)',
                r'Experience\s*([^\n]+)'
            ]
            
            for pattern in exp_patterns:
                match = re.search(pattern, page_text, re.IGNORECASE)
                if match:
                    experience = match.group(1).strip() if match.lastindex else match.group(0).strip()
                    if experience:
                        return experience
                        
        except:
            pass
        return "Experience not specified"

    def _extract_job_id(self, page_text: str, job_url: str) -> str:
        """Extract job ID from page text or URL."""
        try:
            # Extract from URL first
            url_match = re.search(r'/(\d+)-', job_url)
            if url_match:
                return url_match.group(1)
                
            # Look for job ID in text
            id_patterns = [
                r'Req Id:\s*(\d+)',
                r'Job ID:\s*(\d+)',
                r'ID:\s*(\d+)'
            ]
            
            for pattern in id_patterns:
                match = re.search(pattern, page_text, re.IGNORECASE)
                if match:
                    return match.group(1)
                    
        except:
            pass
        return ""

    def _extract_description(self, page_text: str) -> str:
        """Extract job description from page text."""
        try:
            # Find the main description content
            lines = page_text.split('\n')
            description_lines = []
            in_description = False
            
            # Keywords that indicate start of description
            description_starters = [
                'job description', 'role purpose', 'description', 
                'responsibilities', 'key responsibilities'
            ]
            
            # Keywords that indicate end of description
            description_enders = [
                'mandatory skills', 'experience:', 'qualifications:',
                'requirements:', 'apply now', 'share this job'
            ]
            
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                    
                # Check if we're entering description
                if any(starter in line.lower() for starter in description_starters):
                    in_description = True
                    continue
                    
                # Check if we're leaving description
                if any(ender in line.lower() for ender in description_enders):
                    in_description = False
                    continue
                    
                if in_description and len(line) > 20:  # Reasonable description line length
                    description_lines.append(line)
            
            if description_lines:
                return "\n".join(description_lines)
                
        except:
            pass
            
        # Fallback: return everything between title and skills/experience
        return page_text

    def _build_full_description(self, title, location, experience, posting_date, job_id, description, full_text):
        """Build comprehensive job description."""
        sections = [
            f"Job Title: {title}",
            f"Location: {location}",
            f"Experience Required: {experience}",
            f"Posting Date: {posting_date}",
        ]
        
        if job_id:
            sections.append(f"Job ID: {job_id}")
            
        sections.append(f"\nFull Job Details:\n{full_text}")
            
        return "\n".join(sections)

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

    def _get_current_date(self):
        """Get current date for posting_date field."""
        return datetime.now().strftime("%Y-%m-%d")

    def scrape_jobs(self, search_term: str = "", location: str = "", max_pages: int = 10) -> List[JobListing]:
        """Scrape jobs with pagination support."""
        try:
            job_urls = self.get_job_urls(search_term, location, max_pages)
            self.logger.info(f"Found {len(job_urls)} total job URLs to parse")
            
            jobs = []
            for i, job_url in enumerate(job_urls):
                self.logger.info(f"Processing job {i+1}/{len(job_urls)}")
                job = self.parse_job(job_url)
                if job:
                    jobs.append(job)
                time.sleep(self.delay)
            
            return jobs
            
        except Exception as e:
            self.logger.error(f"Error during scraping: {e}")
            return []
        finally:
            self._close_driver()

def main():
    """Test the scraper."""
    scraper = WiproScraper(delay=2.0)
    
    jobs = scraper.scrape_jobs(max_pages=3)  # Scrape first 3 pages for testing
    
    print(f"Found {len(jobs)} jobs")
    
    for job in jobs[:3]:  # Show first 3 jobs
        print(f"\nTitle: {job.title}")
        print(f"Location: {job.location}")
        print(f"Experience: {job.experience_level}")
        print(f"Posted Date: {job.posted_date}")
        print(f"URL: {job.job_url}")
        print("-" * 50)
    
    if jobs:
        scraper.save_to_json(jobs, "wipro_jobs.json")
        scraper.save_to_csv(jobs, "wipro_jobs.csv")
        print(f"\nSaved {len(jobs)} jobs to files")

if __name__ == "__main__":
    main()