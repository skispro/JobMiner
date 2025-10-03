# Tata Steel Job Scraper 🏭💼

A Python-based web scraper that extracts job listings from the [Tata Steel Careers Portal](https://tatasteel.ripplehire.com/candidate/?token=kYAz91uy1lFDi6FeSiRZ&lang=en&source=CAREERSITE#list) using **Selenium** and saves them into structured JSON and CSV files.

## ✨ Features
- Scrapes all available job listings from the Tata Steel careers portal.
- Extracts detailed information including:
  - Job Title
  - Location
  - Experience Requirements
  - Number of Openings
  - Job Description
  - Job URL
- Handles single-page application dynamic content loading.
- Exports data to JSON and CSV files (`tatasteel_jobs.json` and `tatasteel_jobs.csv`).

## 🛠️ Installation

1. **Fork and Clone the repository**
   ```bash
   git clone https://github.com/your-username/JobMiner.git
   cd scrapers/tatasteel
   ```

2. **Set up a virtual environment (optional)**
   ```bash
   python -m venv venv
   source venv/bin/activate   # On Linux/Mac
   venv\Scripts\activate      # On Windows
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```
4. **Run the scrapper**
  ```bash
  python tatasteel.py
  ```
