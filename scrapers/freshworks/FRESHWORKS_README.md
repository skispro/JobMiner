# Freshworks Job Scraper 🏢🔥

A Python-based web scraper that extracts job listings and detailed descriptions from the [Freshworks Careers Portal](https://careers.smartrecruiters.com/Freshworks) using **Requests + BeautifulSoup** and saves them into structured JSON and CSV files.

## ✨ Features
- Scrapes all available job listings from Freshworks’ career portal.
- Extracts detailed information including:
  - Job Title  
  - Location  
  - Posted Date (if available)  
  - Full Job Description  
- Lightweight implementation (no Selenium required).  
- Exports data to:
  - CSV file (`freshworks_jobs.csv`)  
  - JSON file (`freshworks_jobs.json`)  

## 🛠️ Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/your-username/freshworks-job-scraper.git
   cd freshworks-job-scraper