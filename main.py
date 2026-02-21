#!/usr/bin/env python3
"""
Google Scholar Profile Scraper - Self-Contained Version
A complete GUI application that scrapes Google Scholar profiles and saves data to CSV
"""

import sys
import os
import re
import time
import pandas as pd
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QPushButton, QLineEdit, QLabel, 
                             QProgressBar, QMessageBox, QTableWidget, 
                             QTableWidgetItem, QHeaderView, QAbstractItemView,
                             QFileDialog, QSplitter)
from PyQt5.QtCore import QThread, pyqtSignal, Qt
from PyQt5.QtGui import QColor, QDesktopServices
from PyQt5.QtCore import QUrl

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException


# ============================================================================
# SCRAPING FUNCTIONS
# ============================================================================

def scrape_paper_citers(paper_url):
    """
    Scrapes all citers (citing papers) from a Google Scholar paper page.
    """
    import random
    
    # Try Firefox first (common on macOS), then Chrome
    driver = None
    
    # Determine which browser to use with anti-detection settings
    try:
        print("  Trying Firefox...")
        options = webdriver.FirefoxOptions()
        # Don't use headless - Google detects it
        # options.add_argument('--headless')
        options.set_preference("general.useragent.override", 
                             "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
        # Add more realistic preferences
        options.set_preference("dom.webdriver.enabled", False)
        options.set_preference('useAutomationExtension', False)
        driver = webdriver.Firefox(options=options)
        print("  Using Firefox (non-headless to avoid CAPTCHA)")
    except Exception as e:
        print(f"  Firefox failed: {e}")
        try:
            print("  Trying Chrome...")
            options = webdriver.ChromeOptions()
            # Don't use headless - Google detects it
            # options.add_argument('--headless')
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--disable-blink-features=AutomationControlled')
            options.add_experimental_option("excludeSwitches", ["enable-automation"])
            options.add_experimental_option('useAutomationExtension', False)
            options.add_argument('--disable-gpu')
            options.add_argument('--window-size=1920,1080')
            options.add_argument('user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
            driver = webdriver.Chrome(options=options)
            print("  Using Chrome (non-headless to avoid CAPTCHA)")
        except Exception as e2:
            print(f"  Chrome also failed: {e2}")
            raise Exception("Could not start Firefox or Chrome. Please install one of them.")
    
    citers = []
    
    try:
        print(f"  Loading paper page: {paper_url}")
        driver.get(paper_url)
        
        # Random delay to appear more human-like
        delay = random.uniform(3, 5)
        print(f"  Waiting {delay:.1f} seconds...")
        time.sleep(delay)
        
        # Try to find "Cited by" link with multiple strategies
        cited_by_url = None
        
        # Strategy 1: Look for "Cited by" link
        try:
            print("  Trying to find 'Cited by' link...")
            cited_by_link = driver.find_element(By.XPATH, "//a[contains(text(), 'Cited by')]")
            cited_by_url = cited_by_link.get_attribute('href')
            print(f"  Found 'Cited by' link: {cited_by_url}")
        except NoSuchElementException:
            print("  'Cited by' link not found with strategy 1")
        
        # Strategy 2: Look in the page for citation info
        if not cited_by_url:
            try:
                print("  Trying alternative strategy...")
                # Look for any link with 'cites' in the href
                all_links = driver.find_elements(By.TAG_NAME, "a")
                for link in all_links:
                    href = link.get_attribute('href')
                    if href and 'scholar.google.com' in href and 'cites=' in href:
                        cited_by_url = href
                        print(f"  Found citation link: {cited_by_url}")
                        break
            except Exception as e:
                print(f"  Alternative strategy failed: {e}")
        
        if not cited_by_url:
            print("  No 'Cited by' link found - paper may have no citations")
            return []
        
        # Random delay before navigating
        delay = random.uniform(2, 4)
        print(f"  Waiting {delay:.1f} seconds before navigating to citations...")
        time.sleep(delay)
        
        # Navigate to citations page
        print(f"  Navigating to citations page...")
        driver.get(cited_by_url)
        
        # Longer random wait for page load
        delay = random.uniform(4, 6)
        print(f"  Waiting {delay:.1f} seconds for page to load...")
        time.sleep(delay)
        
        # Check for CAPTCHA first
        page_source = driver.page_source.lower()
        if 'captcha' in page_source:
            print("  ⚠️  CAPTCHA DETECTED!")
            print("  Please solve the CAPTCHA in the browser window that opened.")
            print("  After solving it, press ENTER here to continue...")
            input()
            time.sleep(2)
        elif 'unusual traffic' in page_source:
            print("  ⚠️  Google Scholar detected unusual traffic")
            print("  Please complete any verification in the browser window.")
            print("  After completing it, press ENTER here to continue...")
            input()
            time.sleep(2)
        
        # Check if we're on the citations page - try multiple selectors
        citation_page_loaded = False
        
        # Try to find results with different selectors
        try:
            results = driver.find_elements(By.CLASS_NAME, "gs_ri")
            if len(results) > 0:
                citation_page_loaded = True
                print(f"  Citations page loaded successfully (found {len(results)} results)")
        except:
            pass
        
        if not citation_page_loaded:
            try:
                print("  Trying alternative result detection...")
                results = driver.find_elements(By.CLASS_NAME, "gs_r")
                if len(results) > 0:
                    citation_page_loaded = True
                    print(f"  Citations page loaded successfully (found {len(results)} results)")
            except:
                pass
        
        if not citation_page_loaded:
            print("  ❌ Could not find citation results")
            print(f"  Current URL: {driver.current_url}")
            print(f"  Page title: {driver.title}")
            print("\n  If you see a CAPTCHA in the browser, solve it and press ENTER...")
            input()
            time.sleep(2)
            
            # Try again after user input
            results = driver.find_elements(By.CLASS_NAME, "gs_ri")
            if len(results) == 0:
                results = driver.find_elements(By.CLASS_NAME, "gs_r")
            
            if len(results) > 0:
                citation_page_loaded = True
                print(f"  ✓ Found {len(results)} results after CAPTCHA solve")
            else:
                print("  Still no results found. Exiting.")
                return []
        
        # Track seen titles to avoid duplicates
        seen_titles = set()
        
        # Click through all pages
        page_num = 1
        max_retries = 3
        retry_count = 0
        
        while True:
            print(f"  Scraping page {page_num}...")
            
            # Random delay between pages
            if page_num > 1:
                delay = random.uniform(2, 4)
                print(f"  Human-like delay: {delay:.1f} seconds...")
                time.sleep(delay)
            
            try:
                # Scrape current page - use multiple selectors
                paper_rows = driver.find_elements(By.CLASS_NAME, "gs_ri")
                
                if len(paper_rows) == 0:
                    paper_rows = driver.find_elements(By.CLASS_NAME, "gs_r")
                
                print(f"  Found {len(paper_rows)} results on page {page_num}")
                
                if len(paper_rows) == 0:
                    print("  No results found on this page")
                    if page_num == 1:
                        print("  No citations found at all")
                    break
                
                new_items = 0
                for row in paper_rows:
                    citer_data = {}
                    try:
                        # Try to find title with multiple selectors
                        title = None
                        title_elem = None
                        
                        try:
                            title_elem = row.find_element(By.CLASS_NAME, "gs_rt")
                            title = title_elem.text
                        except:
                            try:
                                title_elem = row.find_element(By.CSS_SELECTOR, "h3 a")
                                title = title_elem.text
                            except:
                                continue
                        
                        # Skip duplicates or empty titles
                        if not title or title in seen_titles:
                            continue
                        
                        seen_titles.add(title)
                        citer_data['citer_title'] = title
                        new_items += 1
                        
                        # Get link
                        try:
                            if title_elem:
                                try:
                                    link_elem = title_elem.find_element(By.TAG_NAME, "a")
                                    citer_data['citer_link'] = link_elem.get_attribute('href')
                                except:
                                    citer_data['citer_link'] = title_elem.get_attribute('href')
                            else:
                                citer_data['citer_link'] = None
                        except:
                            citer_data['citer_link'] = None
                        
                        # Get authors, publication, year
                        try:
                            info_elem = row.find_element(By.CLASS_NAME, "gs_a")
                            info_parts = info_elem.text.split(' - ')
                            citer_data['citer_authors'] = info_parts[0] if len(info_parts) > 0 else None
                            citer_data['citer_publication'] = info_parts[1] if len(info_parts) > 1 else None
                            
                            if len(info_parts) > 2:
                                year_match = re.search(r'\b(19|20)\d{2}\b', info_parts[2])
                                citer_data['citer_year'] = year_match.group(0) if year_match else None
                            else:
                                citer_data['citer_year'] = None
                        except:
                            citer_data['citer_authors'] = None
                            citer_data['citer_publication'] = None
                            citer_data['citer_year'] = None
                        
                        citers.append(citer_data)
                    except Exception as e:
                        continue
                
                print(f"  Added {new_items} new citers (total: {len(citers)})")
                
                # Try to go to next page
                try:
                    # Look for next button with multiple selectors
                    next_button = None
                    
                    try:
                        next_button = driver.find_element(By.XPATH, "//button[@aria-label='Next']")
                    except:
                        try:
                            next_button = driver.find_element(By.ID, "gs_nma")
                        except:
                            try:
                                next_button = driver.find_element(By.XPATH, "//a[contains(@href, 'start=')]")
                            except:
                                pass
                    
                    if not next_button:
                        print("  No next button found - this is the last page")
                        break
                    
                    # Check if button is disabled
                    is_disabled = next_button.get_attribute('disabled')
                    has_disabled_class = 'disabled' in (next_button.get_attribute('class') or '')
                    
                    if is_disabled or has_disabled_class:
                        print("  Next button is disabled - reached last page")
                        break
                    
                    # Scroll and click
                    driver.execute_script("arguments[0].scrollIntoView(true);", next_button)
                    time.sleep(random.uniform(1, 2))
                    
                    # Try clicking
                    try:
                        next_button.click()
                    except:
                        driver.execute_script("arguments[0].click();", next_button)
                    
                    page_num += 1
                    retry_count = 0
                    
                except Exception as e:
                    print(f"  Error finding/clicking next button: {e}")
                    break
                
            except Exception as e:
                print(f"  Error on page {page_num}: {e}")
                retry_count += 1
                if retry_count >= max_retries:
                    print(f"  Max retries reached, stopping")
                    break
                time.sleep(2)
                continue
        
        print(f"  ✓ Extracted {len(citers)} total citers")
    
    except Exception as e:
        print(f"  Error in scrape_paper_citers: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        if driver:
            print("\n  Browser will stay open for 5 seconds (in case you need to check)...")
            time.sleep(5)
            try:
                driver.quit()
                print("  Browser closed")
            except:
                pass
    
    return citers
    """
    Scrapes all citers (citing papers) from a Google Scholar paper page.
    """
    # Try Firefox first (common on macOS), then Chrome
    driver = None
    
    # Determine which browser to use
    try:
        print("  Trying Firefox...")
        options = webdriver.FirefoxOptions()
        options.add_argument('--headless')
        options.set_preference("general.useragent.override", 
                             "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
        driver = webdriver.Firefox(options=options)
        print("  Using Firefox")
    except Exception as e:
        print(f"  Firefox failed: {e}")
        try:
            print("  Trying Chrome...")
            options = webdriver.ChromeOptions()
            options.add_argument('--headless')
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--disable-blink-features=AutomationControlled')
            options.add_argument('--disable-gpu')
            options.add_argument('--window-size=1920,1080')
            options.add_argument('user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36')
            driver = webdriver.Chrome(options=options)
            print("  Using Chrome")
        except Exception as e2:
            print(f"  Chrome also failed: {e2}")
            raise Exception("Could not start Firefox or Chrome. Please install one of them.")
    
    citers = []
    
    try:
        print(f"  Loading paper page: {paper_url}")
        driver.get(paper_url)
        time.sleep(3)
        
        # Try to find "Cited by" link with multiple strategies
        cited_by_url = None
        
        # Strategy 1: Look for "Cited by" link
        try:
            print("  Trying to find 'Cited by' link...")
            cited_by_link = driver.find_element(By.XPATH, "//a[contains(text(), 'Cited by')]")
            cited_by_url = cited_by_link.get_attribute('href')
            print(f"  Found 'Cited by' link: {cited_by_url}")
        except NoSuchElementException:
            print("  'Cited by' link not found with strategy 1")
        
        # Strategy 2: Look in the page for citation info
        if not cited_by_url:
            try:
                print("  Trying alternative strategy...")
                # Look for any link with 'cites' in the href
                all_links = driver.find_elements(By.TAG_NAME, "a")
                for link in all_links:
                    href = link.get_attribute('href')
                    if href and 'scholar.google.com' in href and 'cites=' in href:
                        cited_by_url = href
                        print(f"  Found citation link: {cited_by_url}")
                        break
            except Exception as e:
                print(f"  Alternative strategy failed: {e}")
        
        if not cited_by_url:
            print("  No 'Cited by' link found - paper may have no citations")
            return []
        
        # Navigate to citations page
        print(f"  Navigating to citations page...")
        driver.get(cited_by_url)
        time.sleep(5)  # Increased wait time for Google Scholar
        
        # Check if we're on the citations page - try multiple selectors
        citation_page_loaded = False
        
        # Try to find results with different selectors
        try:
            # First try: gs_ri (standard Google Scholar results)
            results = driver.find_elements(By.CLASS_NAME, "gs_ri")
            if len(results) > 0:
                citation_page_loaded = True
                print(f"  Citations page loaded successfully (found {len(results)} results)")
        except:
            pass
        
        if not citation_page_loaded:
            try:
                # Second try: Wait a bit longer and try again
                print("  Waiting longer for page to load...")
                time.sleep(5)
                results = driver.find_elements(By.CLASS_NAME, "gs_ri")
                if len(results) > 0:
                    citation_page_loaded = True
                    print(f"  Citations page loaded successfully (found {len(results)} results)")
            except:
                pass
        
        if not citation_page_loaded:
            try:
                # Third try: Look for the search results container
                print("  Trying alternative result detection...")
                container = driver.find_element(By.ID, "gs_res_ccl_mid")
                if container:
                    citation_page_loaded = True
                    print("  Citations page container found")
            except:
                pass
        
        if not citation_page_loaded:
            print("  Could not verify citations page loaded")
            print(f"  Current URL: {driver.current_url}")
            print(f"  Page title: {driver.title}")
            
            # Try to save screenshot for debugging (if not headless)
            try:
                driver.save_screenshot('/tmp/scholar_debug.png')
                print("  Screenshot saved to /tmp/scholar_debug.png")
            except:
                pass
            
            # Check if there's a CAPTCHA or block
            page_source = driver.page_source.lower()
            if 'captcha' in page_source:
                print("  ERROR: Google Scholar is showing a CAPTCHA")
                return []
            elif 'unusual traffic' in page_source:
                print("  ERROR: Google Scholar detected unusual traffic")
                return []
            
            # Let's try to proceed anyway
            print("  Attempting to proceed anyway...")
        
        # Track seen titles to avoid duplicates
        seen_titles = set()
        
        # Click through all pages
        page_num = 1
        max_retries = 3
        retry_count = 0
        
        while True:
            print(f"  Scraping page {page_num}...")
            
            try:
                # Scrape current page - use multiple selectors
                paper_rows = driver.find_elements(By.CLASS_NAME, "gs_ri")
                
                if len(paper_rows) == 0:
                    # Try alternative selector
                    print("  No gs_ri elements found, trying alternative selectors...")
                    paper_rows = driver.find_elements(By.CLASS_NAME, "gs_r")
                
                print(f"  Found {len(paper_rows)} results on page {page_num}")
                
                if len(paper_rows) == 0:
                    print("  No results found on this page")
                    if page_num == 1:
                        print("  No citations found at all")
                    break
                
                new_items = 0
                for row in paper_rows:
                    citer_data = {}
                    try:
                        # Try to find title with multiple selectors
                        title = None
                        title_elem = None
                        
                        try:
                            title_elem = row.find_element(By.CLASS_NAME, "gs_rt")
                            title = title_elem.text
                        except:
                            try:
                                title_elem = row.find_element(By.CSS_SELECTOR, "h3 a")
                                title = title_elem.text
                            except:
                                continue
                        
                        # Skip duplicates or empty titles
                        if not title or title in seen_titles:
                            continue
                        
                        seen_titles.add(title)
                        citer_data['citer_title'] = title
                        new_items += 1
                        
                        # Get link
                        try:
                            if title_elem:
                                try:
                                    link_elem = title_elem.find_element(By.TAG_NAME, "a")
                                    citer_data['citer_link'] = link_elem.get_attribute('href')
                                except:
                                    citer_data['citer_link'] = title_elem.get_attribute('href')
                            else:
                                citer_data['citer_link'] = None
                        except:
                            citer_data['citer_link'] = None
                        
                        # Get authors, publication, year
                        try:
                            info_elem = row.find_element(By.CLASS_NAME, "gs_a")
                            info_parts = info_elem.text.split(' - ')
                            citer_data['citer_authors'] = info_parts[0] if len(info_parts) > 0 else None
                            citer_data['citer_publication'] = info_parts[1] if len(info_parts) > 1 else None
                            
                            if len(info_parts) > 2:
                                year_match = re.search(r'\b(19|20)\d{2}\b', info_parts[2])
                                citer_data['citer_year'] = year_match.group(0) if year_match else None
                            else:
                                citer_data['citer_year'] = None
                        except:
                            citer_data['citer_authors'] = None
                            citer_data['citer_publication'] = None
                            citer_data['citer_year'] = None
                        
                        citers.append(citer_data)
                    except Exception as e:
                        print(f"  Error extracting row: {e}")
                        continue
                
                print(f"  Added {new_items} new citers (total: {len(citers)})")
                
                # Try to go to next page
                try:
                    # Look for next button with multiple selectors
                    next_button = None
                    
                    try:
                        next_button = driver.find_element(By.XPATH, "//button[@aria-label='Next']")
                    except:
                        try:
                            next_button = driver.find_element(By.ID, "gs_nma")
                        except:
                            try:
                                next_button = driver.find_element(By.XPATH, "//a[contains(@href, 'start=')]")
                            except:
                                pass
                    
                    if not next_button:
                        print("  No next button found - this is the last page")
                        break
                    
                    # Check if button is disabled
                    is_disabled = next_button.get_attribute('disabled')
                    has_disabled_class = 'disabled' in (next_button.get_attribute('class') or '')
                    
                    if is_disabled or has_disabled_class:
                        print("  Next button is disabled - reached last page")
                        break
                    
                    # Scroll and click
                    driver.execute_script("arguments[0].scrollIntoView(true);", next_button)
                    time.sleep(1)
                    
                    # Try clicking with JavaScript if regular click fails
                    try:
                        next_button.click()
                    except:
                        driver.execute_script("arguments[0].click();", next_button)
                    
                    time.sleep(4)  # Wait for next page to load
                    page_num += 1
                    retry_count = 0  # Reset retry count on successful page load
                    
                except Exception as e:
                    print(f"  Error finding/clicking next button: {e}")
                    break
                
            except Exception as e:
                print(f"  Error on page {page_num}: {e}")
                import traceback
                traceback.print_exc()
                retry_count += 1
                if retry_count >= max_retries:
                    print(f"  Max retries reached, stopping")
                    break
                time.sleep(2)
                continue
        
        print(f"  Extracted {len(citers)} total citers")
    
    except Exception as e:
        print(f"  Error in scrape_paper_citers: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        if driver:
            try:
                driver.quit()
                print("  Browser closed")
            except:
                pass
    
    return citers


def scrape_google_scholar_profile(profile_url):
    """
    Scrapes all publications from a Google Scholar profile page.
    """
    # Try Firefox first (common on macOS), then Chrome
    driver = None
    
    try:
        print("Trying Firefox...")
        options = webdriver.FirefoxOptions()
        options.add_argument('--headless')
        options.set_preference("general.useragent.override", 
                             "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36")
        driver = webdriver.Firefox(options=options)
        print("Using Firefox")
    except Exception as e:
        print(f"Firefox failed: {e}")
        try:
            print("Trying Chrome...")
            options = webdriver.ChromeOptions()
            options.add_argument('--headless')
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--disable-blink-features=AutomationControlled')
            options.add_argument('--disable-gpu')
            options.add_argument('--window-size=1920,1080')
            options.add_argument('user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36')
            driver = webdriver.Chrome(options=options)
            print("Using Chrome")
        except Exception as e2:
            print(f"Chrome also failed: {e2}")
            raise Exception("Could not start Firefox or Chrome. Please install one of them.")
    
    all_papers = []
    
    try:
        print(f"Loading profile page...")
        driver.get(profile_url)
        time.sleep(3)
        
        # Click "Show more" button repeatedly
        while True:
            try:
                show_more_button = WebDriverWait(driver, 5).until(
                    EC.presence_of_element_located((By.ID, "gsc_bpf_more"))
                )
                
                if show_more_button.get_attribute('disabled'):
                    print("All papers loaded")
                    break
                
                driver.execute_script("arguments[0].scrollIntoView();", show_more_button)
                time.sleep(0.5)
                show_more_button.click()
                print("Loading more papers...")
                time.sleep(2)
                
            except TimeoutException:
                print("All papers already loaded")
                break
            except Exception as e:
                print(f"Finished loading papers: {e}")
                break
        
        # Extract papers
        print("Extracting paper information...")
        
        try:
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.ID, "gsc_a_b"))
            )
        except TimeoutException:
            print("Error: Could not find publications table")
            return pd.DataFrame()
        
        paper_rows = driver.find_elements(By.CLASS_NAME, "gsc_a_tr")
        print(f"Found {len(paper_rows)} papers")
        
        for idx, row in enumerate(paper_rows, 1):
            paper_data = {}
            
            try:
                # Title and link
                try:
                    title_element = row.find_element(By.CLASS_NAME, "gsc_a_at")
                    paper_data['title'] = title_element.text
                    paper_data['link'] = title_element.get_attribute('href')
                except NoSuchElementException:
                    paper_data['title'] = None
                    paper_data['link'] = None
                
                # Authors
                try:
                    authors_element = row.find_element(By.CLASS_NAME, "gs_gray")
                    paper_data['authors'] = authors_element.text
                except NoSuchElementException:
                    paper_data['authors'] = None
                
                # Publication venue
                try:
                    publication_elements = row.find_elements(By.CLASS_NAME, "gs_gray")
                    if len(publication_elements) > 1:
                        paper_data['publication'] = publication_elements[1].text
                    else:
                        paper_data['publication'] = None
                except (NoSuchElementException, IndexError):
                    paper_data['publication'] = None
                
                # Year
                try:
                    year_element = row.find_element(By.CLASS_NAME, "gsc_a_y")
                    year_text = year_element.text.strip()
                    paper_data['year'] = year_text if year_text else None
                except NoSuchElementException:
                    paper_data['year'] = None
                
                # Citations
                try:
                    citation_element = row.find_element(By.CLASS_NAME, "gsc_a_c")
                    citation_text = citation_element.text.strip()
                    if citation_text and citation_text.isdigit():
                        paper_data['citations'] = int(citation_text)
                    else:
                        paper_data['citations'] = 0
                except NoSuchElementException:
                    paper_data['citations'] = 0
                
                paper_data['paper_id'] = idx
                all_papers.append(paper_data)
                
                if idx % 10 == 0:
                    print(f"Processed {idx}/{len(paper_rows)} papers...")
                
            except Exception as e:
                print(f"Error extracting paper {idx}: {e}")
                continue
    
    finally:
        driver.quit()
    
    df = pd.DataFrame(all_papers)
    
    if not df.empty:
        column_order = ['paper_id', 'title', 'authors', 'publication', 'year', 'citations', 'link']
        df = df[[col for col in column_order if col in df.columns]]
    
    print(f"\nSuccessfully scraped {len(all_papers)} papers")
    return df


# ============================================================================
# THREADS
# ============================================================================

class ScraperThread(QThread):
    """Thread for running the scraper without blocking the GUI"""
    finished = pyqtSignal(object)
    progress = pyqtSignal(str)
    error = pyqtSignal(str)
    
    def __init__(self, url):
        super().__init__()
        self.url = url
        
    def run(self):
        try:
            self.progress.emit("Starting scraper...")
            papers_df = scrape_google_scholar_profile(self.url)
            self.progress.emit(f"Scraped {len(papers_df)} papers successfully!")
            self.finished.emit(papers_df)
        except Exception as e:
            import traceback
            print(f"Scraper error: {e}\n{traceback.format_exc()}")
            self.error.emit(f"Error: {str(e)}")


class CitersThread(QThread):
    """Thread for scraping citers of a specific paper"""
    finished = pyqtSignal(object)
    progress = pyqtSignal(str)
    error = pyqtSignal(str)
    
    def __init__(self, paper_url, paper_title):
        super().__init__()
        self.paper_url = paper_url
        self.paper_title = paper_title
        
    def run(self):
        try:
            self.progress.emit(f"Loading citers for: {self.paper_title[:50]}...")
            citers = scrape_paper_citers(self.paper_url)
            self.progress.emit(f"Found {len(citers)} citers!")
            self.finished.emit(citers)
        except Exception as e:
            import traceback
            print(f"Citers error: {e}\n{traceback.format_exc()}")
            self.error.emit(str(e))


# ============================================================================
# MAIN GUI
# ============================================================================

class MainWindow(QMainWindow):
    """Main application window"""
    
    def __init__(self):
        super().__init__()
        self.papers_df = None
        self.citers_df = None
        self.current_paper_title = None
        self.current_paper_year = None
        self.init_ui()
        
    def init_ui(self):
        self.setWindowTitle("Google Scholar Profile Scraper")
        self.setGeometry(100, 100, 1400, 900)
        
        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Main layout
        main_layout = QVBoxLayout()
        
        # Search section
        search_layout = QHBoxLayout()
        
        url_label = QLabel("Profile URL:")
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("https://scholar.google.com/citations?user=...")
        self.url_input.setText("https://scholar.google.com/citations?user=XvOnO9wAAAAJ&hl=en")
        
        self.search_btn = QPushButton("Search")
        self.search_btn.clicked.connect(self.start_scraping)
        self.search_btn.setFixedWidth(100)
        
        search_layout.addWidget(url_label)
        search_layout.addWidget(self.url_input)
        search_layout.addWidget(self.search_btn)
        
        main_layout.addLayout(search_layout)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximum(0)
        self.progress_bar.hide()
        main_layout.addWidget(self.progress_bar)
        
        # Status label
        self.status_label = QLabel("Ready. Enter a Google Scholar profile URL and click 'Search'.")
        main_layout.addWidget(self.status_label)
        
        # Papers table (60% of window)
        papers_header_layout = QHBoxLayout()
        papers_label = QLabel("<b>Publications</b>")
        self.save_papers_btn = QPushButton("Save Papers to CSV")
        self.save_papers_btn.clicked.connect(self.save_papers_to_csv)
        self.save_papers_btn.setEnabled(False)
        papers_header_layout.addWidget(papers_label)
        papers_header_layout.addStretch()
        papers_header_layout.addWidget(self.save_papers_btn)
        
        main_layout.addLayout(papers_header_layout)
        
        self.papers_table = QTableWidget()
        self.papers_table.setColumnCount(6)
        self.papers_table.setHorizontalHeaderLabels(['#', 'Title', 'Authors', 'Publication', 'Year', 'Citations'])
        self.papers_table.setAlternatingRowColors(True)
        self.papers_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.papers_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.papers_table.verticalHeader().setVisible(False)
        
        # Set column widths
        header = self.papers_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeToContents)
        
        # Connect cell click for citations
        self.papers_table.cellClicked.connect(self.on_paper_cell_clicked)
        
        main_layout.addWidget(self.papers_table, 60)  # 60% height
        
        # Citers table (30% of window)
        citers_header_layout = QHBoxLayout()
        self.citers_title_label = QLabel("<b>Citers</b>")
        self.save_citers_btn = QPushButton("Save Citers to CSV")
        self.save_citers_btn.clicked.connect(self.save_citers_to_csv)
        self.save_citers_btn.setEnabled(False)
        citers_header_layout.addWidget(self.citers_title_label)
        citers_header_layout.addStretch()
        citers_header_layout.addWidget(self.save_citers_btn)
        
        main_layout.addLayout(citers_header_layout)
        
        self.citers_table = QTableWidget()
        self.citers_table.setColumnCount(5)
        self.citers_table.setHorizontalHeaderLabels(['#', 'Title', 'Authors', 'Publication', 'Year'])
        self.citers_table.setAlternatingRowColors(True)
        self.citers_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.citers_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.citers_table.verticalHeader().setVisible(False)
        self.citers_table.cellDoubleClicked.connect(self.open_citer_link)
        
        # Set column widths for citers
        citers_header = self.citers_table.horizontalHeader()
        citers_header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        citers_header.setSectionResizeMode(1, QHeaderView.Stretch)
        citers_header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        citers_header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        citers_header.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        
        main_layout.addWidget(self.citers_table, 30)  # 30% height
        
        central_widget.setLayout(main_layout)
        
        # Show welcome message
        self.show_welcome_messages()
    
    def show_welcome_messages(self):
        """Show welcome messages in both tables"""
        # Papers table
        self.papers_table.setRowCount(1)
        self.papers_table.setColumnCount(1)
        self.papers_table.setHorizontalHeaderLabels([''])
        welcome_item = QTableWidgetItem("Enter a Google Scholar profile URL and click 'Search' to begin")
        welcome_item.setTextAlignment(Qt.AlignCenter)
        welcome_item.setForeground(QColor(128, 128, 128))
        self.papers_table.setItem(0, 0, welcome_item)
        self.papers_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        
        # Citers table
        self.citers_table.setRowCount(1)
        self.citers_table.setColumnCount(1)
        self.citers_table.setHorizontalHeaderLabels([''])
        citers_item = QTableWidgetItem("Click on any citation count to view citing papers here")
        citers_item.setTextAlignment(Qt.AlignCenter)
        citers_item.setForeground(QColor(128, 128, 128))
        self.citers_table.setItem(0, 0, citers_item)
        self.citers_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
    
    def start_scraping(self):
        """Start the scraping process"""
        url = self.url_input.text().strip()
        
        if not url:
            QMessageBox.warning(self, "Error", "Please enter a valid URL")
            return
        
        if "scholar.google.com/citations" not in url:
            QMessageBox.warning(self, "Error", "Please enter a valid Google Scholar profile URL")
            return
        
        # Disable button and show progress
        self.search_btn.setEnabled(False)
        self.save_papers_btn.setEnabled(False)
        self.progress_bar.show()
        self.status_label.setText("Scraping profile...")
        
        # Start scraper thread
        self.scraper_thread = ScraperThread(url)
        self.scraper_thread.finished.connect(self.on_scraping_finished)
        self.scraper_thread.progress.connect(self.update_status)
        self.scraper_thread.error.connect(self.on_scraping_error)
        self.scraper_thread.start()
    
    def update_status(self, message):
        """Update status label"""
        self.status_label.setText(message)
    
    def on_scraping_finished(self, papers_df):
        """Handle scraping completion"""
        self.papers_df = papers_df
        self.search_btn.setEnabled(True)
        self.progress_bar.hide()
        
        if papers_df is None or papers_df.empty:
            QMessageBox.warning(self, "No Results", "No papers found or error occurred")
            return
        
        # Populate papers table
        self.populate_papers_table(papers_df)
        self.save_papers_btn.setEnabled(True)
        self.status_label.setText(f"Loaded {len(papers_df)} papers. Click on citations to view citers.")
    
    def on_scraping_error(self, error_message):
        """Handle scraping errors"""
        self.search_btn.setEnabled(True)
        self.progress_bar.hide()
        self.status_label.setText("Error occurred")
        QMessageBox.critical(self, "Error", error_message)
    
    def populate_papers_table(self, df):
        """Populate the papers table with data"""
        self.papers_table.setColumnCount(6)
        self.papers_table.setHorizontalHeaderLabels(['#', 'Title', 'Authors', 'Publication', 'Year', 'Citations'])
        self.papers_table.setRowCount(len(df))
        
        for idx, row in df.iterrows():
            # Paper ID
            id_item = QTableWidgetItem(str(row.get('paper_id', idx + 1)))
            id_item.setTextAlignment(Qt.AlignCenter)
            self.papers_table.setItem(idx, 0, id_item)
            
            # Title
            title = row.get('title', 'N/A')
            title_item = QTableWidgetItem(title)
            title_item.setForeground(QColor(26, 13, 171))
            link = row.get('link', None)
            if link:
                title_item.setData(Qt.UserRole, link)
                title_item.setToolTip("Double-click to open")
            self.papers_table.setItem(idx, 1, title_item)
            
            # Authors
            authors = row.get('authors', 'N/A')
            authors_item = QTableWidgetItem(authors)
            self.papers_table.setItem(idx, 2, authors_item)
            
            # Publication
            publication = row.get('publication', 'N/A')
            pub_item = QTableWidgetItem(publication)
            self.papers_table.setItem(idx, 3, pub_item)
            
            # Year
            year = str(row.get('year', 'N/A'))
            year_item = QTableWidgetItem(year)
            year_item.setTextAlignment(Qt.AlignCenter)
            self.papers_table.setItem(idx, 4, year_item)
            
            # Citations (clickable)
            citations = row.get('citations', 0)
            cite_item = QTableWidgetItem(str(citations))
            cite_item.setTextAlignment(Qt.AlignCenter)
            if citations > 0:
                cite_item.setForeground(QColor(66, 133, 244))  # Blue
                cite_item.setToolTip("Click to view citers")
            self.papers_table.setItem(idx, 5, cite_item)
        
        # Restore column widths
        header = self.papers_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeToContents)
    
    def on_paper_cell_clicked(self, row, column):
        """Handle cell clicks in papers table"""
        # If citations column clicked
        if column == 5:
            cite_item = self.papers_table.item(row, 5)
            if cite_item and int(cite_item.text()) > 0:
                self.load_citers_for_paper(row)
        # If title column double-clicked
        elif column == 1:
            title_item = self.papers_table.item(row, 1)
            if title_item:
                link = title_item.data(Qt.UserRole)
                if link:
                    QDesktopServices.openUrl(QUrl(link))
    
    def load_citers_for_paper(self, row):
        """Load citers for a specific paper"""
        if self.papers_df is None:
            return
        
        paper_row = self.papers_df.iloc[row]
        paper_title = paper_row['title']
        paper_year = paper_row['year']
        paper_link = paper_row['link']
        
        if not paper_link:
            QMessageBox.warning(self, "Error", "No link available for this paper")
            return
        
        self.current_paper_title = paper_title
        self.current_paper_year = paper_year
        
        # Update citers title
        self.citers_title_label.setText(f"<b>Citers for:</b> {paper_title[:60]}... ({paper_year})")
        
        # Show loading
        self.citers_table.setRowCount(1)
        self.citers_table.setColumnCount(1)
        self.citers_table.setHorizontalHeaderLabels([''])
        loading_item = QTableWidgetItem("Loading citers...")
        loading_item.setTextAlignment(Qt.AlignCenter)
        self.citers_table.setItem(0, 0, loading_item)
        
        self.status_label.setText(f"Loading citers for: {paper_title[:50]}...")
        self.save_citers_btn.setEnabled(False)
        
        # Clean up previous thread
        if hasattr(self, 'citers_thread') and self.citers_thread.isRunning():
            self.citers_thread.quit()
            self.citers_thread.wait()
        
        # Start citers thread
        self.citers_thread = CitersThread(paper_link, paper_title)
        self.citers_thread.finished.connect(self.on_citers_loaded)
        self.citers_thread.progress.connect(self.update_status)
        self.citers_thread.error.connect(self.on_citers_error)
        self.citers_thread.start()
    
    def on_citers_loaded(self, citers):
        """Handle citers loading completion"""
        self.citers_df = pd.DataFrame(citers) if citers else pd.DataFrame()
        
        if not citers:
            self.citers_table.setRowCount(1)
            self.citers_table.setColumnCount(1)
            self.citers_table.setHorizontalHeaderLabels([''])
            no_item = QTableWidgetItem("No citers found for this paper")
            no_item.setTextAlignment(Qt.AlignCenter)
            self.citers_table.setItem(0, 0, no_item)
            self.status_label.setText("No citers found")
            return
        
        # Populate citers table
        self.citers_table.setColumnCount(5)
        self.citers_table.setHorizontalHeaderLabels(['#', 'Title', 'Authors', 'Publication', 'Year'])
        self.citers_table.setRowCount(len(citers))
        
        for idx, citer in enumerate(citers):
            # Number
            num_item = QTableWidgetItem(str(idx + 1))
            num_item.setTextAlignment(Qt.AlignCenter)
            self.citers_table.setItem(idx, 0, num_item)
            
            # Title
            title = citer.get('citer_title', 'N/A')
            title_item = QTableWidgetItem(title)
            title_item.setForeground(QColor(26, 13, 171))
            link = citer.get('citer_link', None)
            if link:
                title_item.setData(Qt.UserRole, link)
                title_item.setToolTip("Double-click to open")
            self.citers_table.setItem(idx, 1, title_item)
            
            # Authors
            authors = citer.get('citer_authors', 'N/A')
            authors_item = QTableWidgetItem(authors)
            self.citers_table.setItem(idx, 2, authors_item)
            
            # Publication
            publication = citer.get('citer_publication', 'N/A')
            pub_item = QTableWidgetItem(publication)
            self.citers_table.setItem(idx, 3, pub_item)
            
            # Year
            year = str(citer.get('citer_year', 'N/A'))
            year_item = QTableWidgetItem(year)
            year_item.setTextAlignment(Qt.AlignCenter)
            self.citers_table.setItem(idx, 4, year_item)
        
        # Restore column widths
        header = self.citers_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        
        self.status_label.setText(f"Loaded {len(citers)} citers")
        self.save_citers_btn.setEnabled(True)
    
    def on_citers_error(self, error_message):
        """Handle citers loading error"""
        self.status_label.setText("Error loading citers")
        self.citers_table.setRowCount(1)
        self.citers_table.setColumnCount(1)
        self.citers_table.setHorizontalHeaderLabels([''])
        error_item = QTableWidgetItem(f"Error: {error_message}")
        error_item.setTextAlignment(Qt.AlignCenter)
        error_item.setForeground(QColor(255, 0, 0))
        self.citers_table.setItem(0, 0, error_item)
    
    def open_citer_link(self, row, column):
        """Open link when citer is double-clicked"""
        if column == 1:  # Title column
            item = self.citers_table.item(row, column)
            if item:
                link = item.data(Qt.UserRole)
                if link:
                    QDesktopServices.openUrl(QUrl(link))
    
    def save_papers_to_csv(self):
        """Save papers table to CSV"""
        if self.papers_df is None or self.papers_df.empty:
            QMessageBox.warning(self, "No Data", "No papers to save")
            return
        
        filename, _ = QFileDialog.getSaveFileName(
            self, "Save Papers", "scholar_papers.csv", "CSV Files (*.csv)"
        )
        
        if filename:
            try:
                self.papers_df.to_csv(filename, index=False)
                QMessageBox.information(self, "Success", f"Papers saved to {filename}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to save: {str(e)}")
    
    def save_citers_to_csv(self):
        """Save citers table to CSV with paper title and year as filename"""
        if self.citers_df is None or self.citers_df.empty:
            QMessageBox.warning(self, "No Data", "No citers to save")
            return
        
        # Create filename from paper title and year
        if self.current_paper_title and self.current_paper_year:
            # Clean title for filename
            clean_title = re.sub(r'[^\w\s-]', '', self.current_paper_title)
            clean_title = re.sub(r'[-\s]+', '_', clean_title)
            clean_title = clean_title[:50]  # Limit length
            default_name = f"{clean_title}_{self.current_paper_year}_citers.csv"
        else:
            default_name = "citers.csv"
        
        filename, _ = QFileDialog.getSaveFileName(
            self, "Save Citers", default_name, "CSV Files (*.csv)"
        )
        
        if filename:
            try:
                self.citers_df.to_csv(filename, index=False)
                QMessageBox.information(self, "Success", f"Citers saved to {filename}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to save: {str(e)}")


# ============================================================================
# MAIN
# ============================================================================

def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
