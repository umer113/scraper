import requests
from bs4 import BeautifulSoup
import pandas as pd

# Function to scrape property data from a given URL
def scrape_property_data(property_url):
    response = requests.get(property_url)
    soup = BeautifulSoup(response.text, 'html.parser')

    # Scrape name
    name = soup.find('h1', class_='entry-title entry-prop').get_text(strip=True)

    # Scrape address
    address_div = soup.find('div', class_='property_categs')
    address = address_div.get_text(strip=True) if address_div else 'N/A'

    # Scrape price
    price_div = soup.find('div', class_='price_area')
    price = price_div.get_text(strip=True) if price_div else 'N/A'

    # Scrape description
    description_div = soup.find('div', id='tab_property_description')
    description = description_div.get_text(strip=True) if description_div else 'N/A'

    # Scrape area from characteristics
    area = 'N/A'
    characteristics_div = soup.find('div', id='tab_property_overview')
    if characteristics_div:
        overview_elements = characteristics_div.find_all('ul', class_='overview_element')
        for overview in overview_elements:
            if 'm²' or 'm2' in overview.get_text():
                area = overview.get_text(strip=True)

    # Scrape characteristics
    characteristics = {}
    if characteristics_div:
        overview_elements = characteristics_div.find_all('ul', class_='overview_element')
        
        for overview in overview_elements:
            # Extract all 'li' elements inside each 'ul'
            list_items = overview.find_all('li')

            # For each 'li' element, check if it's a key-value pair or just a single item
            for i in range(0, len(list_items) - 1, 2):
                key = list_items[i].get_text(strip=True)
                value = list_items[i + 1].get_text(strip=True)

                # If the value contains m², name the key "Area"
                if 'm²' in value or 'm2' in value:
                    key = 'Area'

                characteristics[key] = value

            # Handle cases where 'li' does not have a colon (like "3 Bedrooms")
            for li in overview.find_all('li'):
                if li.find('svg'):  # Checking if it's an SVG (icon) next to the text
                    key = li.get_text(strip=True)
                    value = li.find_next_sibling('li').get_text(strip=True) if li.find_next_sibling('li') else 'N/A'
                    
                    # If the value contains m², name the key "Area"
                    if 'm²' in value or 'm2' in value:
                        key = 'Area'

                    characteristics[key] = value




    # Scrape property type
    property_type_div = soup.find('div', class_='property_title_label actioncat')
    property_type = property_type_div.get_text(strip=True) if property_type_div else 'N/A'

    # Scrape transaction type
    transaction_type_div = soup.find('div', class_='property_title_label')
    transaction_type = transaction_type_div.get_text(strip=True) if transaction_type_div else 'N/A'

    # Scrape latitude and longitude
    latitude = longitude = 'N/A'
    script_tag = soup.find('script', id='googlecode_property-js-extra')
    if script_tag:
        script_content = script_tag.string
        if 'general_latitude' in script_content and 'general_longitude' in script_content:
            latitude = script_content.split('"general_latitude":"')[1].split('"')[0]
            longitude = script_content.split('"general_longitude":"')[1].split('"')[0]

    # Return all the scraped data
    return {
        'Name': name,
        'Address': address,
        'Price': price,
        'Description': description,
        'Area': area,
        'Characteristics': characteristics,
        'Property Type': property_type,
        'Transaction Type': transaction_type,
        'Latitude': latitude,
        'Longitude': longitude,
        'URL': property_url
    }

# Function to scrape all property URLs and their data
def scrape_all_properties(base_url, start_page=1):
    page_number = start_page
    property_urls = []

    while True:
        url = f"{base_url}{page_number}/"
        response = requests.get(url)

        if response.status_code != 200:
            print(f"Failed to retrieve page {page_number}. Stopping.")
            break

        soup = BeautifulSoup(response.text, 'html.parser')
        property_divs = soup.find_all('div', class_='listing-unit-img-wrapper')

        if not property_divs:
            print(f"No property URLs found on page {page_number}. Stopping.")
            break

        for div in property_divs:
            anchor_tag = div.find('a')
            if anchor_tag and 'href' in anchor_tag.attrs:
                property_urls.append(anchor_tag['href'])

        print(f"Scraped {len(property_divs)} properties from page {page_number}.")
        page_number += 1

    return property_urls

# Base URL for pagination
base_url = 'https://www.samoarealty.co/property_action_category/sales/page/'

# Scrape all property URLs
property_urls = scrape_all_properties(base_url)

# Initialize an empty list to hold all property data
all_properties_data = []

# Visit each property URL and scrape the data
for property_url in property_urls:
    property_data = scrape_property_data(property_url)
    print(property_data)
    all_properties_data.append(property_data)

# Convert the data to a DataFrame
df = pd.DataFrame(all_properties_data)

# Save the data to a single Excel file
df.to_excel('samoarealty_properties.xlsx', index=False)
print("All property data saved to 'samoarealty_properties.xlsx'")
