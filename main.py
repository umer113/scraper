import requests
from bs4 import BeautifulSoup
import pandas as pd
import os
import re

# Function to scrape property URLs from a single page
def scrape_property_urls(base_url, page_num):
    if "?" in base_url:
        url = f"{base_url.split('?')[0]}/page/{page_num}/?" + base_url.split('?')[1]
    else:
        url = f"{base_url}page/{page_num}/"

    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')

    print(url)
    
    # Find all property divs
    property_divs = soup.find_all('div', class_='item active')
    
    # Extract property URLs
    property_urls = []
    for div in property_divs:
        a_tag = div.find('a')  # Find the <a> tag inside the div
        if a_tag and 'href' in a_tag.attrs:
            property_urls.append(a_tag['href'])
    
    return property_urls

# Function to scrape property details from a single property URL
def scrape_property_details(property_url):
    response = requests.get(property_url)
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # Extract name
    name_tag = soup.find('h1', class_='entry-title entry-prop')
    name = name_tag.text.strip() if name_tag else '-'

    # Extract description
    description_tag = soup.find('div', class_='wpestate_property_description')
    description = description_tag.get_text(separator=" ", strip=True) if description_tag else '-'

    # Extract address
    address_tag = soup.find('div', class_='property_categs')
    address = address_tag.text.strip() if address_tag else '-'

    # price
    price_tag = soup.find('div', class_='price_area')
    price = price_tag.get_text(separator=" ", strip=True) if price_tag else 'N/A'
            
    # Extract characteristics
    characteristics = {}
    characteristics_sections = soup.find_all('div', class_='panel-body')
    if len(characteristics_sections) > 1:
        second_characteristics_section = characteristics_sections[1]
        characteristics_tags = second_characteristics_section.find_all('div', class_='listing_detail')
        for char_tag in characteristics_tags:
            label = char_tag.find('strong')
            if label:
                key = label.text.strip().rstrip(':')
                value = ''.join(sibling.strip() for sibling in label.next_siblings if isinstance(sibling, str) or sibling.name == 'span').strip()
                characteristics[key] = value

    # Extract property size or lot size
    property_size = characteristics.get('Property Size', '-')
    if property_size == '-':
        property_size = characteristics.get('Property Lot Size', '-')
    if price in ['Starting Million', 'Million', '', 'Million Million']:
        price = characteristics.get("Price", "N/A")

    # Extract property type and transaction type
    property_type_tag = soup.find('div', class_='property_title_label actioncat')
    property_type = property_type_tag.text.strip() if property_type_tag else '-'
    transaction_type_tag = soup.find('div', class_='property_title_label')
    transaction_type = transaction_type_tag.text.strip() if transaction_type_tag else '-'

    # Extract features
    features = {}
    features_tags = soup.find_all('div', class_='feature_chapter_name')
    for feature_tag in features_tags:
        category = feature_tag.text.strip()
        features[category] = [detail_tag.text.strip() for detail_tag in feature_tag.find_next_siblings('div', class_='listing_detail')]

    # Extract latitude and longitude
    map_tag = soup.find('div', id='googleMapSlider')
    latitude = map_tag['data-cur_lat'] if map_tag and 'data-cur_lat' in map_tag.attrs else None
    longitude = map_tag['data-cur_long'] if map_tag and 'data-cur_long' in map_tag.attrs else None

    area = characteristics.get("Property Size", "-") 
    if area == '-':
        area = characteristics.get("Property Lot Size", "-")

    return {
        'URL': property_url,
        'Name': name,
        'Description': description,
        'Address': address,
        'Price': price,
        'Area (ft2)': area,
        'Characteristics': characteristics,
        'Property Type': property_type,
        'Transaction Type': transaction_type,
        'Features': features,
        'Latitude': latitude,
        'Longitude': longitude
    }

# Function to scrape all property URLs and details from a given base URL
def scrape_data_for_url(base_url):
    if "?" in base_url:
        initial_url = f"{base_url.split('?')[0]}/page/1/?" + base_url.split('?')[1]
    else:
        initial_url = f"{base_url}page/1/"

    response = requests.get(initial_url)
    soup = BeautifulSoup(response.text, 'html.parser')

    pagination_links = soup.find_all('li', class_='roundright')
    total_pages = int(pagination_links[-1].find('a')['href'].split('/')[-2]) if pagination_links else 1

    print(f"Total pages for {base_url}: {total_pages}")
    all_property_urls = []
    for page in range(1, total_pages + 1):
        all_property_urls.extend(scrape_property_urls(base_url, page))
    
    print(f"Found {len(all_property_urls)} property URLs for {base_url}")
    all_properties = [scrape_property_details(url) for url in all_property_urls]
    
    # Save the data to an Excel file in the artifacts folder
    os.makedirs('artifacts', exist_ok=True)
    base_url_cleaned = re.sub(r'[^a-zA-Z0-9]', '_', base_url.strip('/').replace('https://', ''))
    output_file = f"artifacts/{base_url_cleaned}.xlsx"
    pd.DataFrame(all_properties).to_excel(output_file, index=False)
    print(f"Data saved to {output_file}")

# Array of base URLs to scrape
base_urls = [
   'https://boahiyaa.com/maldives-properties-for-rent/',
]

# Loop through all base URLs and scrape data
for base_url in base_urls:
    scrape_data_for_url(base_url)
