import os
import requests
from bs4 import BeautifulSoup
import pandas as pd
import re

class BinaAzScraper:
    def __init__(self, urls):
        self.base_url = 'https://bina.az'
        self.urls = urls
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'
        }
        # Create the output directory if it doesn't exist
        self.output_dir = 'output'
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)

    def fetch_page(self, url):
        response = requests.get(url, headers=self.headers)
        response.raise_for_status()
        return BeautifulSoup(response.text, 'html.parser')

    def parse(self, soup):
        data = []
        # Extract property URLs
        property_urls = [a['href'] for a in soup.select('a.item_link')]
        for url in property_urls:
            full_url = self.base_url + url
            data.append(self.parse_property(full_url))

        # Navigate to the next page
        next_page = soup.select_one('a[rel="next"]')
        if next_page:
            next_page_url = self.base_url + next_page['href']
            next_soup = self.fetch_page(next_page_url)
            data.extend(self.parse(next_soup))

        return data

    def parse_property(self, url):
        soup = self.fetch_page(url)
        name = soup.select_one('h1.product-title').get_text(strip=True)
        price = soup.select_one('div.product-price__i--bold .price-val').get_text() + ' ' + soup.select_one('div.product-price__i--bold .price-cur').get_text()
        address = soup.select_one('div.product-map__left__address').get_text(strip=True)
        area = next((span.get_text() for span in soup.select('span.product-properties__i-value') if 'm²' in span.get_text()), None)
        property_type = soup.select('a.product-breadcrumbs__i-link')[1].get_text(strip=True)
        transaction_type = soup.select_one('a.product-breadcrumbs__i-link').get_text()
        
        # Scrape latitude and longitude directly from the div
        description_div = soup.select_one('div.product-description__content')
        if description_div:
            description = description_div.get_text(separator='\n', strip=True)  # Extract all text, handling <br> as new lines
        else:
            description = None
        
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
            'address': address,
            'latitude': latitude,
            'longitude': longitude,
            'area': area,
            'property_type': property_type,
            'transaction_type': transaction_type,
        }
        print(property_data)
        return property_data


    def save_to_excel(self, data, url):
        df = pd.DataFrame(data)
        file_name = os.path.join(self.output_dir, re.sub(r'[^\w]', '_', url.replace('https://', '')) + '.xlsx')
        df.to_excel(file_name, index=False, engine='openpyxl')
        print(f'Saved data to {file_name}')

    def run(self):
        for url in self.urls:
            soup = self.fetch_page(url)
            data = self.parse(soup)
            self.save_to_excel(data, url)

if __name__ == "__main__":
    urls = [
        'https://bina.az/alqi-satqi/menziller?price_to=10000000',
        # Add more URLs as needed
    ]
    scraper = BinaAzScraper(urls)
    scraper.run()
