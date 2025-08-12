from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import csv
import json
import time
import random
import logging
import os
from urllib.parse import urljoin

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('selenium_book_scraper.log'),
        logging.StreamHandler()
    ]
)

class SeleniumBookScraper:
    def __init__(self):
        self.base_url = "https://books.toscrape.com/"
        self.catalogue_url = "https://books.toscrape.com/catalogue/"
        self.all_books = []
        self.output_dir = "scraped_data"
        
        # Set up Chrome options
        chrome_options = Options()
        chrome_options.add_argument("--headless")  # Run in headless mode
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        
        # Initialize the WebDriver
        self.driver = webdriver.Chrome(
            service=Service(ChromeDriverManager().install()),
            options=chrome_options
        )
        self.driver.set_page_load_timeout(30)
        
        # Create output directory if it doesn't exist
        os.makedirs(self.output_dir, exist_ok=True)

    def get_page(self, url):
        """Fetch a page with Selenium and return its source"""
        try:
            # Random delay to be more polite
            time.sleep(random.uniform(0.5, 2.0))
            
            self.driver.get(url)
            
            # Wait for the products to load
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CLASS_NAME, "product_pod")))
            
            return self.driver.page_source
            
        except Exception as e:
            logging.error(f"Failed to fetch {url}: {e}")
            return None
        finally:
            pass  # Add finally clause to satisfy the try statement requirement

    def scrape_book_details(self, book_url):
        """Scrape detailed information from a book's individual page"""
        try:
            self.driver.get(book_url)
            
            # Wait for the product page to load
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CLASS_NAME, "product_page")))
            
            soup = BeautifulSoup(self.driver.page_source, 'lxml')
            
            # Extract additional details available on the book page
            product_page = soup.find('article', class_='product_page')
            if not product_page:
                return None
                
            description = product_page.find('meta', attrs={'name': 'description'})['content'].strip()
            upc = product_page.find('th', string='UPC').find_next_sibling('td').text
            product_type = product_page.find('th', string='Product Type').find_next_sibling('td').text
            tax = product_page.find('th', string='Tax').find_next_sibling('td').text
            reviews = product_page.find('th', string='Number of reviews').find_next_sibling('td').text
            
            return {
                'description': description,
                'upc': upc,
                'product_type': product_type,
                'tax': tax,
                'reviews': reviews
            }
        except Exception as e:
            logging.error(f"Error scraping book details from {book_url}: {e}")
            return None
        finally:
            pass

    def scrape_page(self, page_num):
        """Scrape a single catalogue page"""
        page_url = f"{self.catalogue_url}page-{page_num}.html"
        logging.info(f"Scraping page {page_num}: {page_url}")
        
        page_source = self.get_page(page_url)
        if not page_source:
            return False
            
        soup = BeautifulSoup(page_source, 'lxml')
        books = soup.select(".product_pod")
        
        if not books:
            logging.warning(f"No books found on page {page_num}")
            return False
            
        for book in books:
            try:
                title = book.h3.a["title"]
                raw_price = book.select_one(".price_color").text.strip()
                price = float(raw_price.replace('£', '').replace('Â', '').strip())
                availability = book.select_one(".availability").text.strip()
                rating = book.p["class"][1]  # e.g., "Three"
                relative_link = book.h3.a["href"]
                link = urljoin(self.catalogue_url, relative_link)
                
                # Get additional details from the book's page
                book_details = self.scrape_book_details(link)
                
                book_data = {
                    "title": title,
                    "price": price,
                    "availability": availability,
                    "rating": rating,
                    "url": link
                }
                
                if book_details:
                    book_data.update(book_details)
                
                self.all_books.append(book_data)
                
            except Exception as e:
                logging.error(f"Error processing book on page {page_num}: {e}")
                continue
                
        return True

    def scrape_multiple_pages(self, start_page=1, end_page=2):
        """Scrape a range of pages"""
        for page_num in range(start_page, end_page + 1):
            if not self.scrape_page(page_num):
                break
                
    def save_to_csv(self, filename="books_data.csv"):
        """Save scraped data to CSV file"""
        filepath = os.path.join(self.output_dir, filename)
        try:
            with open(filepath, "w", newline="", encoding="utf-8") as file:
                if not self.all_books:
                    logging.warning("No data to save to CSV")
                    return
                    
                fieldnames = list(self.all_books[0].keys())
                writer = csv.DictWriter(file, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(self.all_books)
            logging.info(f"Data successfully saved to {filepath}")
        except Exception as e:
            logging.error(f"Failed to save CSV: {e}")

    def save_to_json(self, filename="books_data.json"):
        """Save scraped data to JSON file"""
        filepath = os.path.join(self.output_dir, filename)
        try:
            with open(filepath, "w", encoding="utf-8") as file:
                json.dump(self.all_books, file, indent=4, ensure_ascii=False)
            logging.info(f"Data successfully saved to {filepath}")
        except Exception as e:
            logging.error(f"Failed to save JSON: {e}")

    def run(self, start_page=1, end_page=2):
        """Run the scraper"""
        logging.info("Starting Selenium scraper...")
        start_time = time.time()
        
        try:
            self.scrape_multiple_pages(start_page, end_page)
            self.save_to_csv()
            self.save_to_json()
        except Exception as e:
            logging.error(f"Scraping failed: {e}")
        finally:
            self.driver.quit()
            
        elapsed_time = time.time() - start_time
        logging.info(f"Scraping complete. Scraped {len(self.all_books)} books in {elapsed_time:.2f} seconds.")

if __name__ == "__main__":
    scraper = SeleniumBookScraper()
    scraper.run(start_page=1, end_page=2)  # Scrape first 2 pages