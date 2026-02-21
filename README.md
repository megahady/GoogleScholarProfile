<img width="1440" height="900" alt="image" src="https://github.com/user-attachments/assets/e4212521-37d7-4e8f-8771-c4ef5b5f4a99" />

# Google Scholar Profile Scraper

This project is a GUI-based application for scraping Google Scholar profiles and extracting publication data, including citations and citing papers. The application uses Selenium for web scraping and PyQt5 for the graphical user interface.

---

## Features

- **Google Scholar Profile Scraping**: Extracts all publications from a Google Scholar profile, including title, authors, publication venue, year, and citation count.
- **Citing Papers Scraping**: Retrieves details of papers that cite a specific publication.
- **Save to CSV**: Allows saving the scraped data (publications and citing papers) to CSV files.
- **Interactive GUI**: User-friendly interface for entering profile URLs, viewing data, and saving results.

---

## Requirements

To run this project, you need the following:

- Python 3.7+
- Google Chrome or Mozilla Firefox (installed on your system)
- ChromeDriver or GeckoDriver (compatible with your browser version)

### Python Dependencies

Install the required Python packages using the following command:

pip install -r [requirements.txt](http://_vscodecontentref_/0)

python main.py


### Notes
- CAPTCHA Handling: If Google Scholar detects unusual traffic, you may encounter a CAPTCHA. Solve the CAPTCHA in the browser window that opens, then press ENTER in the terminal to continue.
- Headless Mode: The scraper avoids headless mode to reduce the likelihood of detection by Google Scholar.


### Troubleshooting
- Browser Not Found: Ensure that Chrome or Firefox is installed and the corresponding driver is in your system's PATH.
- CAPTCHA Issues: If CAPTCHA appears frequently, reduce the scraping speed or use a different IP address.
- Dependencies: Ensure all dependencies are installed using pip install -r requirements.txt.
```bash
