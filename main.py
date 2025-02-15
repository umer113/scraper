import requests
from bs4 import BeautifulSoup
import pandas as pd
import os

class BinaAzScraper:
    def __init__(self, start_url, start_page, end_page):
        self.start_url = start_url
        self.base_url = "https://bina.az"
        self.start_page = start_page
        self.end_page = end_page
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'
        }
        self.all_data = []

    def fetch_page(self, url):
        response = requests.get(url, headers=self.headers)
        response.raise_for_status()
        return BeautifulSoup(response.text, 'html.parser')

    def parse(self, soup):
        data = []
        property_urls = [a['href'] for a in soup.select('a.item_link')]
        for url in property_urls:
            full_url = self.base_url + url
            data.append(self.parse_property(full_url))
        return data

    def parse_property(self, url):
        soup = self.fetch_page(url)
        name = soup.select_one('h1.product-title').get_text(strip=True)
        address = soup.select_one('div.product-map__left__address').get_text(strip=True)
        area = next((span.get_text() for span in soup.select('span.product-properties__i-value') if 'm²' in span.get_text()), None)
        
        property_type = "Apartments"
        transaction_type = "sale"

        price_val = soup.select_one('div.product-price__i--bold .price-val')
        price_cur = soup.select_one('div.product-price__i--bold .price-cur')
        price = f"{price_val.get_text(strip=True)} {price_cur.get_text(strip=True)}" if price_val and price_cur else "N/A"

        description_div = soup.select_one('div.product-description__content')
        description = description_div.get_text(separator='\n', strip=True) if description_div else None
        
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
            'characteristics': str(characteristics),  # Store as string
            'area': area,
            'property_type': property_type,
            'transaction_type': transaction_type
        }
        return property_data

    def save_all_data_to_excel(self):
        df = pd.DataFrame(self.all_data)
        os.makedirs('artifacts', exist_ok=True)
        file_name = 'artifacts/bina_az_all_pages.xlsx'
        df.to_excel(file_name, index=False, engine='openpyxl')
        print(f'Saved all data to {file_name}')

    def run(self):
        for page_num in range(self.start_page, self.end_page + 1):
            url = f'{self.start_url}?page={page_num}'
            print(f'Scraping page {page_num}: {url}')
            soup = self.fetch_page(url)
            data = self.parse(soup)
            self.all_data.extend(data)
        self.save_all_data_to_excel()

if __name__ == "__main__":
    start_url = 'https://bina.az/alqi-satqi/heyet-evleri'
    start_page = 1
    end_page = 300
    scraper = BinaAzScraper(start_url, start_page, end_page)
    scraper.run()
