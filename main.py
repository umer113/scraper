import os
import time
import requests
from bs4 import BeautifulSoup
import pandas as pd

class BinaAzScraper:
    def __init__(self, base_url, start_page, end_page):
        self.base_url = base_url
        self.start_page = start_page
        self.end_page = end_page
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'
        }

    def fetch_page(self, url, retries=3, delay=5):
        for attempt in range(retries):
            try:
                response = requests.get(url, headers=self.headers)
                response.raise_for_status()
                return BeautifulSoup(response.text, 'html.parser')
            except requests.exceptions.HTTPError as e:
                print(f"HTTPError on {url}: {e}")
                if 500 <= response.status_code < 600:
                    # Server error, retry after a delay
                    print(f"Retrying {url} in {delay} seconds... (Attempt {attempt + 1}/{retries})")
                    time.sleep(delay)
                else:
                    # Non-retriable error, skip this URL
                    print(f"Skipping {url} due to non-retriable error.")
                    return None
            except Exception as e:
                print(f"Failed to fetch {url}: {e}")
                return None
        print(f"Failed to fetch {url} after {retries} retries.")
        return None

    def parse(self, soup):
        data = []
        # Extract property URLs
        property_urls = [a['href'] for a in soup.select('a.item_link')]
        for url in property_urls:
            full_url = self.base_url + url
            property_data = self.parse_property(full_url)
            if property_data:
                data.append(property_data)
        return data

    def parse_property(self, url):
        soup = self.fetch_page(url)
        if soup is None:
            return None
        
        try:
            name = soup.select_one('h1.product-title').get_text(strip=True)
            price = soup.select_one('div.product-price__i--bold .price-val').get_text() + ' ' + soup.select_one('div.product-price__i--bold .price-cur').get_text()
            address = soup.select_one('div.product-map__left__address').get_text(strip=True)
            area = next((span.get_text() for span in soup.select('span.product-properties__i-value') if 'm²' in span.get_text()), None)

            # Static property type and transaction type
            property_type = "house"
            transaction_type = "rent"

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
        except Exception as e:
            print(f"Error parsing property data from {url}: {e}")
            return None

    def save_to_excel(self, data, page_num):
        # Create output directory if it doesn't exist
        os.makedirs('output', exist_ok=True)

        df = pd.DataFrame(data)
        file_name = f'output/bina_az_page_{page_num}.xlsx'
        df.to_excel(file_name, index=False, engine='openpyxl')
        print(f'Saved data for page {page_num} to {file_name}')

    def run(self):
        for page_num in range(self.start_page, self.end_page + 1):
            url = f'{self.base_url}?page={page_num}'
            print(f'Scraping page {page_num}: {url}')
            soup = self.fetch_page(url)
            if soup is not None:
                data = self.parse(soup)
                if data:
                    self.save_to_excel(data, page_num)

if __name__ == "__main__":
    base_url = 'https://bina.az/kiraye/menziller'
    start_page = 1
    end_page = 400
    scraper = BinaAzScraper(base_url, start_page, end_page)
    scraper.run()
