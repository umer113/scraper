import requests
from bs4 import BeautifulSoup
import json
from urllib.parse import urljoin
import pandas as pd
import re
import os

# Base URL of the website
base_url = 'https://www.bahamasrealty.com'
main_url = 'https://www.bahamasrealty.com/listings/?status=Active,Pending,Active+Under+Contract,Closed,CNT,PCG'

# Start with the first page
page_number = 1
consecutive_empty_pages = 0
property_count = 0

# List to store scraped data
scraped_data = []

# List of keywords to search in the description
keywords = ['commercial', 'condo', 'house', 'land', 'multi-family']

while consecutive_empty_pages < 3:
    print(f"Scraping page number {page_number}")

    url = f'{main_url}?page={page_number}'

    try:
        response = requests.get(url)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, 'html.parser')

        script_tag = soup.find('script', {'type': 'application/json', 'id': 'data-listings'})
        print(script_tag)

        if script_tag:
            json_data = json.loads(script_tag.string)
            data_scraped = False

            for property in json_data:
                name = property.get('usmPropertyName', None)
                address = property.get('address', {}).get('display', 'N/A')
                price = property.get('listPrice', 'N/A')

                if name or address != 'N/A' or price != 'N/A':
                    property_count += 1
                    data_scraped = True

                    description = property.get('publicRemarks', 'N/A')
                    area = property.get('buildingAreaTotal', 'N/A')
                    bedrooms = property.get('bedroomsTotal', 'N/A')
                    bathrooms_total = property.get('bathroomsTotalInteger', 'N/A')
                    lot_size_acres = property.get('lotSizeAcres', 'N/A')

                    characteristics = {
                        'bedrooms': bedrooms,
                        'bathrooms_total': bathrooms_total,
                        'area': area,
                        'lot_size_acres': lot_size_acres
                    }

                    transaction_type = 'rent' if 'rent' in url.lower() else 'sale' if 'sale' in url.lower() else 'N/A'
                    property_type = property.get('usmPropertyType') or property.get('propertySubType', [])

                    if not property_type:
                        description_lower = description.lower()
                        for keyword in keywords:
                            if keyword in description_lower:
                                property_type = keyword.capitalize()
                                break
                        else:
                            property_type = 'N/A'

                    latitude = property.get('latitude', 'N/A')
                    longitude = property.get('longitude', 'N/A')
                    property_url = urljoin(base_url, property.get('usmDetailPath', ''))

                    if not name:
                        try:
                            property_response = requests.get(property_url)
                            property_response.raise_for_status()
                            property_soup = BeautifulSoup(property_response.text, 'html.parser')
                            meta_tag = property_soup.find('meta', {'property': 'og:title'})
                            name = meta_tag['content'] if meta_tag and 'content' in meta_tag.attrs else "N/A"
                        except requests.exceptions.RequestException as e:
                            print(f"Failed to retrieve property name from {property_url}: {e}")
                            name = "N/A"

                    scraped_data.append({
                        'Name': name,
                        'Address': address,
                        'Price': price,
                        'Description': description,
                        'Area': characteristics['area'],
                        'Lot Size (Acres)': characteristics['lot_size_acres'],
                        'Bedrooms': characteristics['bedrooms'],
                        'Bathrooms (Total)': characteristics['bathrooms_total'],
                        'Transaction Type': transaction_type,
                        'Property Type': property_type,
                        'Latitude': latitude,
                        'Longitude': longitude,
                        'Property URL': property_url
                    })

                    print(scraped_data[-1])
            consecutive_empty_pages = 0 if data_scraped else consecutive_empty_pages + 1
        else:
            print(f"No data-listings found on page {page_number}")
            consecutive_empty_pages += 1

    except requests.exceptions.HTTPError as err:
        print(f"HTTP error occurred on page {page_number}: {err}")
        break

    page_number += 1

print(f"Total number of properties: {property_count}")

# Save the scraped data to an Excel file in the 'artifacts' directory
if scraped_data:
    os.makedirs("artifacts", exist_ok=True)  # Ensure the directory exists
    safe_filename = re.sub(r'[^\w\-_\. ]', '_', main_url)
    filename = os.path.join("artifacts", f"{safe_filename}.xlsx")
    
    df = pd.DataFrame(scraped_data)
    df.to_excel(filename, index=False)
    print(f"Data saved to {filename}")
else:
    print("No data was scraped.")
