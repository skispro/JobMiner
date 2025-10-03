# Amazon Job Scraper

**amazon_scraper.py** – Advanced Python web scraper that extracts comprehensive job information from Amazon’s official careers site ([amazon.jobs](https://www.amazon.jobs)).

## Overview

This scraper goes beyond basic job listings to extract detailed information from each Amazon job page, including:
- Complete job descriptions
- Location details
- Qualifications and requirements
- Posted dates
- Direct application URLs

## Files

### `amazon_scraper.py`
- **Purpose**: Production scraper for Amazon India job listings
- **Default**: Scrapes jobs for a given search term (e.g., “software engineer”)
- **Use Case**: Targeted job extraction with rich job detail parsing


### Output Format
Generates CSV and JSON files with the following fields:
- `title`
- `company`
- `location`
- `description`
- `posted_date`
- `job_url`
- `experience_level`

## Installation

```bash
pip install -r requirements.txt