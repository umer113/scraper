import requests
from bs4 import BeautifulSoup
import pandas as pd
import re
import os
import time
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

class BinaAzScraper:
    def __init__(self, start_url, start_page, end_page):
        self.start_url = start_url
        self.base_url = "https://bina.az"
        self.start_page = start_page
        self.end_page = end_page
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'
        }
        # Set up retry mechanism
        self.session = requests.Session()
        retries = Retry(total=5, backoff_factor=1, status_forcelist=[502, 503, 504])
        self.session.mount('http://', HTTPAdapter(max_retries=retries))
        self.session.mount('https://', HTTPAdapter(max_retries=retries))

    def fetch_page(self, url):
        try:
            # Retry mechanism with headers and delay between requests
            response = self.session.get(url, headers=self.headers)
            response.raise_for_status()
            return BeautifulSoup(response.text, 'html.parser')
        except requests.exceptions.RequestException as e:
            print(f"Error fetching {url}: {e}")
            return None

    def parse(self, soup):
        if not soup:
            return []
        data = []
        # Extract property URLs
        property_urls = [a['href'] for a in soup.select('a.item_link')]
        for url in property_urls:
            full_url = self.base_url + url
            data.append(self.parse_property(full_url))

        return data

    def parse_property(self, url):
        soup = self.fetch_page(url)
        if not soup:
            return {}

        name = soup.select_one('h1.product-title').get_text(strip=True)
        address = soup.select_one('div.product-map__left__address').get_text(strip=True)
        area = next((span.get_text() for span in soup.select('span.product-properties__i-value') if 'm²' in span.get_text()), None)
        
        # Static property type and transaction type
        property_type = "old building apartments"
        transaction_type = "rent"

        if transaction_type == 'sale':
            price = soup.select_one('div.product-price__i--bold .price-val').get_text() + ' ' + soup.select_one('div.product-price__i--bold .price-cur').get_text()
        else:
            price_value = soup.select_one('div.product-price__i--bold .price-val').get_text(strip=True)
            price_currency = soup.select_one('div.product-price__i--bold .price-cur').get_text(strip=True)
            price_period = soup.select_one('div.product-price__i--bold .price-per').get_text(strip=True)
            price = f"{price_value} {price_currency}{price_period}"

        description_div = soup.select_one('div.product-description__content')
        description = description_div.get_text(separator='\n', strip=True) if description_div else None
        
        # Scrape latitude and longitude directly from the div
        map_div = soup.select_one('div#item_map')
        latitude = map_div['data-lat'] if map_div else None
        longitude = map_div['data-lng'] if map_div else None

        characteristics = {}
        characteristics_divs = soup.select('div.product-properties__column .product-properties__i')
        for div in characteristics_divs:
            label = div.select_one('label.product-properties__i-name').get_text(strip=True)
            value = div.select_one('span.product-properties__i-value').get_text(strip=True)
            characteristics[label] = value

        property_data = {
            'url': url,
            'name': name,
            'price': price,
            'description': description,
            'address': address,
            'latitude': latitude,
            'longitude': longitude,
            'characteristics': characteristics,
            'area': area,
            'property_type': property_type,   # Statically defined
            'transaction_type': transaction_type,   # Statically defined
        }
        print(property_data)
        return property_data

    def save_to_excel(self, data, page_num):
        df = pd.DataFrame(data)
        os.makedirs('artifacts', exist_ok=True)  # Create 'artifacts' directory if it doesn't exist
        file_name = f'artifacts/bina_az_page_{page_num}.xlsx'
        df.to_excel(file_name, index=False, engine='openpyxl')
        print(f'Saved data for page {page_num} to {file_name}')

    def run(self):
        for page_num in range(self.start_page, self.end_page + 1):
            url = f'{self.start_url}?page={page_num}'
            print(f'Scraping page {page_num}: {url}')
            soup = self.fetch_page(url)
            data = self.parse(soup)
            self.save_to_excel(data, page_num)
            time.sleep(2)  # Add a delay of 2 seconds between each request

if __name__ == "__main__":
    start_url = 'https://bina.az/kiraye/menziller/kohne-tikili'
    start_page = 1
    end_page = 400
    scraper = BinaAzScraper(start_url, start_page, end_page)
    scraper.run()
