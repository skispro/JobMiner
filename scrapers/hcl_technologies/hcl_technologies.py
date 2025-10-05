"""
HCL Technologies Scraper for JobMiner.

This scraper extracts job listings from HCL Technologies careers website.
"""

import sys
import os
from typing import List, Optional
from urllib.parse import urljoin, quote
import requests
from bs4 import BeautifulSoup
import time
import re

# Add parent directory to path to import base_scraper
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
from base_scraper import BaseScraper, JobListing


class HclTechnologiesScraper(BaseScraper):
    """
    HCL Technologies job scraper.
    """
    
    def __init__(self, delay: float = 2.0):
        """Initialize the HCL Technologies scraper."""
        super().__init__(delay=delay)
        self.base_url = "https://www.hcltech.com"
        self.search_url = f"{self.base_url}/careers/careers-in-india"
    
    def _fetch_page_with_headers(self, url: str) -> Optional[str]:
        """Fetch HTML content with proper headers for HCL website."""
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
        }
        
        try:
            self.logger.info(f"Fetching: {url}")
            response = self.session.get(url, headers=headers, timeout=60, verify=True)
            response.raise_for_status()
            
            # Add delay to be respectful
            time.sleep(self.delay)
            
            self.logger.info(f"Successfully fetched {len(response.text)} characters")
            return response.text
            
        except requests.exceptions.Timeout:
            self.logger.error(f"Timeout error fetching {url}")
            return None
        except requests.exceptions.ConnectionError:
            self.logger.error(f"Connection error fetching {url}")
            return None
        except Exception as e:
            self.logger.error(f"Error fetching {url}: {e}")
            return None
    
    def _clean_text_advanced(self, text: str) -> str:
        """Advanced text cleaning for HCL content."""
        if not text:
            return ""
        
        # Remove extra whitespace and normalize
        text = re.sub(r'\s+', ' ', text.strip())
        # Remove special characters that might cause issues
        text = re.sub(r'[^\w\s\-.,;:()\[\]{}/@#$%&*+=|\\<>?!"\']', ' ', text)
        return text
    
    def get_job_urls(self, search_term: str, location: str = "", max_pages: int = 1) -> List[str]:
        """
        Get job URLs from HCL Technologies careers page.
        HCL appears to have a single page with all jobs loaded.
        """
        job_urls = []
        
        # HCL careers page appears to be a single page with all jobs
        html = self._fetch_page_with_headers(self.search_url)
        if not html:
            return job_urls
        
        soup = BeautifulSoup(html, "html.parser")
        
        # Find the specific table with the exact class structure
        table = soup.select_one('table.table.table-hover.table-striped.views-table.views-view-table.cols-6')
        if not table:
            # Fallback to any table with jobs
            table = soup.select_one('table.views-view-table')
        
        if not table:
            self.logger.warning("Could not find job table")
            return job_urls
        
        # Find job table rows in tbody
        job_rows = table.select('tbody tr')
        
        for row in job_rows:
            try:
                # Extract job title and URL using the exact header structure
                title_elem = row.select_one('td[headers="view-field-designation-table-column"] a')
                if not title_elem:
                    # Fallback selectors
                    title_elem = row.select_one('td.views-field-field-designation a')
                
                if title_elem:
                    href = title_elem.get('href', '')
                    if href:
                        job_url = urljoin(self.base_url, href)
                        job_urls.append(job_url)
                        
            except Exception as e:
                self.logger.error(f"Error extracting job URL from row: {e}")
                continue
        
        return job_urls
    
    def parse_job(self, job_url: str) -> Optional[JobListing]:
        """
        Parse a single job listing from HCL Technologies.
        """
        html = self._fetch_page_with_headers(job_url)
        if not html:
            return None
        
        soup = BeautifulSoup(html, "html.parser")
        
        try:
            # Extract job title from detail page
            title_elem = soup.select_one('h1.page-title, .job-title, h1')
            title = self._clean_text_advanced(title_elem.get_text()) if title_elem else "N/A"
            
            # Extract detailed job description
            description_selectors = [
                '.field--name-body .field__item',
                '.job-description',
                '.field--name-field-job-description .field__item',
                '.content .field__item',
                'article .content',
                'main .content',
                '.job-detail-content'
            ]
            
            description = ""
            for selector in description_selectors:
                desc_elem = soup.select_one(selector)
                if desc_elem:
                    # Remove unwanted elements
                    for unwanted in desc_elem.select('nav, header, .breadcrumb, .tabs, script, style'):
                        unwanted.decompose()
                    description = self._clean_text_advanced(desc_elem.get_text(separator='\n', strip=True))
                    if description and len(description) > 100:  # Ensure we got substantial content
                        break
            
            # If no specific description found, try to get main content
            if not description or len(description) < 100:
                content_area = soup.select_one('main, .main-content, article, .page-content')
                if content_area:
                    for unwanted in content_area.select('nav, header, .breadcrumb, .tabs, script, style, .sidebar'):
                        unwanted.decompose()
                    description = self._clean_text_advanced(content_area.get_text(separator='\n', strip=True))
            
            # Try to extract specific sections
            requirements = ""
            responsibilities = ""
            
            # Look for requirements section
            req_patterns = [
                r'(?i)(requirements?|qualifications?|skills?\s+required|must\s+have)[\s:]*(.+?)(?=responsibilities?|duties|role|$)',
                r'(?i)(required\s+skills?)[\s:]*(.+?)(?=responsibilities?|duties|role|$)'
            ]
            
            for pattern in req_patterns:
                match = re.search(pattern, description, re.DOTALL)
                if match:
                    requirements = self._clean_text_advanced(match.group(2))[:500]  # Limit length
                    break
            
            # Look for responsibilities section
            resp_patterns = [
                r'(?i)(responsibilities?|duties|role\s+description|job\s+description)[\s:]*(.+?)(?=requirements?|qualifications?|skills|$)',
                r'(?i)(key\s+responsibilities?)[\s:]*(.+?)(?=requirements?|qualifications?|skills|$)'
            ]
            
            for pattern in resp_patterns:
                match = re.search(pattern, description, re.DOTALL)
                if match:
                    responsibilities = self._clean_text_advanced(match.group(2))[:500]  # Limit length
                    break
            
            # Build comprehensive description
            desc_parts = []
            if description:
                desc_parts.append(description)
            if requirements:
                desc_parts.append(f"\nRequirements: {requirements}")
            if responsibilities:
                desc_parts.append(f"\nResponsibilities: {responsibilities}")
            
            final_description = "\n".join(desc_parts) if desc_parts else "Detailed description not available"
            
            # Extract basic info from the job listing table (fallback)
            location = "N/A"
            skills = None
            experience = None
            posted_date = None
            
            job = JobListing(
                title=title,
                company="HCL Technologies Limited",
                location=location,
                description=final_description,
                posted_date=posted_date,
                job_url=job_url,
                experience_level=experience,
                job_type=skills
            )
            
            return job
            
        except Exception as e:
            self.logger.error(f"Error parsing job details for {job_url}: {e}")
            return None
    
    def _parse_job_from_table_row(self, row, base_url: str) -> Optional[JobListing]:
        """
        Parse job information directly from table row.
        This is used as a fallback or primary method for basic job info.
        """
        try:
            # Extract job title and URL using the exact header structure
            title_elem = row.select_one('td[headers="view-field-designation-table-column"] a')
            if not title_elem:
                # Fallback selectors
                title_elem = row.select_one('td.views-field-field-designation a')
            if not title_elem:
                return None
                
            title = self._clean_text_advanced(title_elem.get_text())
            job_url = urljoin(base_url, title_elem.get('href', ''))
            
            # Extract primary skills using exact header structure
            skills_elem = row.select_one('td[headers="view-field-skills-table-column"]')
            if not skills_elem:
                skills_elem = row.select_one('td.views-field-field-skills')
            skills = self._clean_text_advanced(skills_elem.get_text()) if skills_elem else "N/A"
            
            # Extract post date using exact header structure
            date_elem = row.select_one('td[headers="view-field-updated-date-table-column"]')
            if not date_elem:
                date_elem = row.select_one('td.views-field-field-updated-date')
            posted_date = self._clean_text_advanced(date_elem.get_text()) if date_elem else "N/A"
            
            # Extract location using exact header structure
            location_elem = row.select_one('td[headers="view-field-kenexa-jobs-location-table-column"]')
            if not location_elem:
                location_elem = row.select_one('td.views-field-field-kenexa-jobs-location')
            location = self._clean_text_advanced(location_elem.get_text()) if location_elem else "N/A"
            
            # Extract experience using exact header structure
            exp_elem = row.select_one('td[headers="view-field-experience-table-column"]')
            if not exp_elem:
                exp_elem = row.select_one('td.views-field-field-experience')
            experience = self._clean_text_advanced(exp_elem.get_text()) if exp_elem else "N/A"
            
            # Build basic description
            basic_description = f"Primary Skills: {skills}\nExperience Required: {experience}"
            
            job = JobListing(
                title=title,
                company="HCL Technologies Limited",
                location=location,
                description=basic_description,
                posted_date=posted_date,
                job_url=job_url,
                experience_level=experience if experience != "N/A" else None,
                job_type=skills if skills != "N/A" else None
            )
            
            return job
            
        except Exception as e:
            self.logger.error(f"Error parsing job row: {e}")
            return None
    
    def scrape_jobs(self, search_term: str, location: str = "", max_pages: int = 1) -> List[JobListing]:
        """
        Override to use HCL-specific scraping approach.
        HCL has a single page with all jobs, so we'll extract from the table directly.
        """
        self.logger.info(f"Starting scrape for '{search_term}' in '{location}'")
        
        # Get the main careers page
        html = self._fetch_page_with_headers(self.search_url)
        if not html:
            self.logger.error("Failed to fetch HCL careers page")
            return []
        
        soup = BeautifulSoup(html, "html.parser")
        
        # Find the specific table with the exact class structure
        table = soup.select_one('table.table.table-hover.table-striped.views-table.views-view-table.cols-6')
        if not table:
            # Fallback to any table with jobs
            table = soup.select_one('table.views-view-table')
        
        if not table:
            self.logger.warning("Could not find job table")
            return []
        
        # Find job table rows in tbody
        job_rows = table.select('tbody tr')
        self.logger.info(f"Found {len(job_rows)} job rows")
        
        jobs = []
        for i, row in enumerate(job_rows, 1):
            self.logger.info(f"Processing job {i}/{len(job_rows)}")
            
            # Parse basic job info from table row
            job = self._parse_job_from_table_row(row, self.base_url)
            if job:
                # Apply filters if provided, but be more lenient
                matches_search = True
                matches_location = True
                
                if search_term:
                    search_lower = search_term.lower()
                    matches_search = (
                        search_lower in job.title.lower() or
                        (job.job_type and search_lower in job.job_type.lower()) or
                        (job.description and search_lower in job.description.lower())
                    )
                
                if location:
                    location_lower = location.lower()
                    matches_location = location_lower in job.location.lower()
                
                # If no filters provided or filters match, include the job
                if matches_search and matches_location:
                    jobs.append(job)
                else:
                    self.logger.debug(f"Job filtered out: {job.title} (search: {matches_search}, location: {matches_location})")
        
        self.logger.info(f"Successfully scraped {len(jobs)} jobs")
        return jobs
    



def test_with_sample_html():
    """Test the scraper with sample HTML data."""
    sample_html = '''
    <div class="view-content row">
        <div data-drupal-views-infinite-scroll-content-wrapper="" class="views-infinite-scroll-content-wrapper clearfix">
            <div class="table-responsive col" data-table-msg="Job Offers">
                <table class="table table-hover table-striped views-table views-view-table cols-6">
                    <thead>
                        <tr>
                            <th class="views-field views-field-field-designation">Job Title</th>
                            <th class="views-field views-field-field-skills">Primary Skills</th>
                            <th class="views-field views-field-field-updated-date">Post date</th>
                            <th class="views-field views-field-field-kenexa-jobs-location">Location</th>
                            <th class="views-field views-field-field-experience">Experience</th>
                            <th class="views-field views-field-dropbutton">Action</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr>
                            <td class="views-field views-field-field-designation">
                                <a href="/jobs/associate-consultant-21">Associate consultant</a>
                            </td>
                            <td class="views-field views-field-field-skills">Identity Management Operations</td>
                            <td class="views-field views-field-field-updated-date">Oct. 1, 2025</td>
                            <td class="views-field views-field-field-kenexa-jobs-location">Bangalore</td>
                            <td class="views-field views-field-field-experience"></td>
                            <td class="views-field views-field-dropbutton">
                                <div class="dropbutton-wrapper">
                                    <ul class="dropbutton">
                                        <li><a href="/jobs/associate-consultant-21">View Job</a></li>
                                    </ul>
                                </div>
                            </td>
                        </tr>
                        <tr>
                            <td class="views-field views-field-field-designation">
                                <a href="/jobs/sr-enterprise-architect">Sr. enterprise architect</a>
                            </td>
                            <td class="views-field views-field-field-skills">Python</td>
                            <td class="views-field views-field-field-updated-date">Sept. 29, 2025</td>
                            <td class="views-field views-field-field-kenexa-jobs-location">Noida</td>
                            <td class="views-field views-field-field-experience">&gt;11 Years</td>
                            <td class="views-field views-field-dropbutton">
                                <div class="dropbutton-wrapper">
                                    <ul class="dropbutton">
                                        <li><a href="/jobs/sr-enterprise-architect">View Job</a></li>
                                    </ul>
                                </div>
                            </td>
                        </tr>
                    </tbody>
                </table>
            </div>
        </div>
    </div>
    '''
    
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(sample_html, 'html.parser')
    
    scraper = HclTechnologiesScraper()
    
    # Extract jobs from table rows
    job_rows = soup.select('tbody tr')
    jobs = []
    
    for row in job_rows:
        job = scraper._parse_job_from_table_row(row, scraper.base_url)
        if job:
            jobs.append(job)
    
    print(f"Found {len(jobs)} jobs from sample HTML")
    
    for i, job in enumerate(jobs, 1):
        print(f"\n--- Job {i} ---")
        print(f"Title: {job.title}")
        print(f"Location: {job.location}")
        print(f"Skills: {job.job_type}")
        print(f"Experience: {job.experience_level}")
        print(f"Posted: {job.posted_date}")
        print(f"URL: {job.job_url}")


def main():
    """Test the scraper."""
    print("Testing HCL Technologies Scraper")
    print("=" * 40)
    
    # Test with sample HTML first
    print("\n1. Testing with sample HTML data:")
    test_with_sample_html()
    
    print("\n" + "=" * 40)
    print("2. Testing with live website:")
    
    scraper = HclTechnologiesScraper()
    
    jobs = scraper.scrape_jobs(
        search_term="python",
        location="bangalore",
        max_pages=1
    )
    
    print(f"Found {len(jobs)} jobs from live website")
    
    if jobs:
        scraper.save_to_json(jobs, "hcl_technologies_jobs.json")
        scraper.save_to_csv(jobs, "hcl_technologies_jobs.csv")
        
        # Print first few jobs as examples
        for i, job in enumerate(jobs[:3], 1):
            print(f"\n--- Job {i} ---")
            print(f"Title: {job.title}")
            print(f"Location: {job.location}")
            print(f"Skills: {job.job_type}")
            print(f"Experience: {job.experience_level}")
            print(f"Posted: {job.posted_date}")


if __name__ == "__main__":
    main()
