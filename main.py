import os
import requests
from bs4 import BeautifulSoup
import json
import pandas as pd
import re

class BinaAzScraper:
    def __init__(self, base_url, start_page, end_page):
        self.base_url = base_url
        self.start_page = start_page
        self.end_page = end_page
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'
        }

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
        return data

    def parse_property(self, url):
        soup = self.fetch_page(url)
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

    def save_to_excel(self, data, page_num):
        # Create output directory if it doesn't exist
        os.makedirs('output', exist_ok=True)
        df = pd.DataFrame(data)
        file_name = f'output/bina_az_page_{page_num}.xlsx'
        df.to_excel(file_name, index=False, engine='openpyxl')
        print(f'Saved data for page {page_num} to {file_name}')

    def run(self):
        all_listings = []
        for page_num in range(self.start_page, self.end_page + 1):
            url = f'{self.base_url}?page={page_num}'
            print(f'Scraping page {page_num}: {url}')
            soup = self.fetch_page(url)
            data = self.parse(soup)
            self.save_to_excel(data, page_num)

            all_listings.extend(data)
            print(f"Page {page_num} scraped. Total listings: {len(all_listings)}")

        return all_listings


def scrape_listings(urls):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'
    }

    for base_url in urls:
        page_number = 1
        all_listings = []

        while True:
            print("===================================================================")
            print(f"Scraping page number: {page_number}")
            url = f"{base_url}?page={page_number}"
            print(url)

            response = requests.get(url, headers=headers)

            if response.status_code == 200:
                print("Successfully fetched the page.")
                soup = BeautifulSoup(response.content, 'html.parser')

                script_tag = soup.find("script", id="__NEXT_DATA__")

                if script_tag:
                    print("Found the script tag.")
                    try:
                        data = json.loads(script_tag.string)
                        listings_data = data['props']['pageProps']['searchResult']['listings']

                        if not listings_data:
                            print("No data found in JSON. Stopping scrape for this URL.")
                            break

                        for listing in listings_data:
                            property_data = listing.get('property', {})
                            location_data = property_data.get('location', {})
                            coordinates = location_data.get('coordinates', {})

                            name = property_data.get('title', '')
                            price_value = property_data.get('price', {}).get('value', '-')
                            currency = property_data.get('price', {}).get('currency', '')
                            period = property_data.get('price', {}).get('period', '')
                            price = f"{price_value} {currency}/{period}" if price_value != '-' else '-'             
                            address = location_data.get('full_name', '')
                            description = property_data.get('description', '-')
                            property_type = property_data.get('property_type', '-')
                            transaction_type = property_data.get('offering_type', '-')
                            area = property_data.get('size', {}).get('value', '-')
                            amenities = ', '.join(property_data.get('amenity_names', []))
                            latitude = coordinates.get('lat', '')
                            longitude = coordinates.get('lon', '')
                            characteristics = {
                                'Property Type': property_type,
                                'Property Size': f"{area} square meters" if area else '-',
                                'Bedrooms': property_data.get('bedrooms', '-'),
                                'Bathrooms': property_data.get('bathrooms', '-'),
                                'Available From': property_data.get('listed_date', '-'),
                            }
                            property_url = 'https://www.propertyfinder.bh' + property_data.get('details_path', '-')

                            listing_data = {
                                'Name': name,
                                'Price': price,
                                'Address': address,
                                'Description': description,
                                'Property Type': property_type,
                                'Transaction Type': transaction_type,
                                'Area': str(area) + " square meters",
                                'Amenities': amenities,
                                'Characteristics': characteristics,
                                'Latitude': latitude,
                                'Longitude': longitude,
                                'Property URL': property_url
                            }
                            print("listing:", listing_data)
                            all_listings.append(listing_data)

                        page_number += 1
                    except json.JSONDecodeError as e:
                        print("Error parsing JSON:", e)
                        break
                else:
                    print(f"No script tag found on page {page_number}. Ending scrape for {base_url}.")
                    break
            else:
                print(f'Failed to retrieve the webpage. Status code: {response.status_code}')
                break


if __name__ == "__main__":
    base_url = 'https://bina.az/kiraye/menziller/yeni-tikili'
    start_page = 401
    end_page = 565
    scraper = BinaAzScraper(base_url, start_page, end_page)
    scraper.run()

    # Example of using the scrape_listings function
    urls = [
        "https://www.propertyfinder.bh/en/buy/properties-for-sale.html"
    ]
    scrape_listings(urls)
