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

    print(f"Scraping URL: {url}")
    
    # Find all property divs
    property_divs = soup.find_all('div', class_='item active')
    
    # Extract property URLs
    property_urls = []
    for div in property_divs:
        a_tag = div.find('a')
        if a_tag and 'href' in a_tag.attrs:
            property_urls.append(a_tag['href'])
    
    return property_urls

# Function to scrape property details from a single property URL
def scrape_property_details(property_url):
    response = requests.get(property_url)
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # Extract details (name, description, address, price, etc.)
    name_tag = soup.find('h1', class_='entry-title entry-prop')
    name = name_tag.text.strip() if name_tag else '-'
    description_tag = soup.find('div', class_='wpestate_property_description')
    description = description_tag.get_text(separator=" ", strip=True) if description_tag else '-'
    address_tag = soup.find('div', class_='property_categs')
    address = address_tag.text.strip() if address_tag else '-'
    price_tag = soup.find('div', class_='price_area')
    price = price_tag.get_text(separator=" ", strip=True) if price_tag else 'N/A'

    characteristics = {}
    characteristics_sections = soup.find_all('div', class_='panel-body')
    if len(characteristics_sections) > 1:
        second_characteristics_section = characteristics_sections[1]
        characteristics_tags = second_characteristics_section.find_all('div', class_='listing_detail')
        for char_tag in characteristics_tags:
            label = char_tag.find('strong')
            if label:
                key = label.text.strip().rstrip(':')
                value = ''.join(sibling.strip() for sibling in label.next_siblings if sibling.name == 'span' or isinstance(sibling, str))
                characteristics[key] = value.strip()

    property_size = characteristics.get('Property Size', '-')
    if property_size == '-':
        property_size = characteristics.get('Property Lot Size', '-')
    if price in ['Starting Million', 'Million', '', "Million Million"]:
        price = characteristics.get("Price","N/A")

    property_type_tag = soup.find('div', class_='property_title_label actioncat')
    property_type = property_type_tag.text.strip() if property_type_tag else '-'
    transaction_type_tag = soup.find('div', class_='property_title_label')
    transaction_type = transaction_type_tag.text.strip() if transaction_type_tag else '-'

    features = {}
    features_tags = soup.find_all('div', class_='feature_chapter_name')
    for feature_tag in features_tags:
        category = feature_tag.text.strip()
        features[category] = [detail_tag.text.strip() for detail_tag in feature_tag.find_next_siblings('div', class_='listing_detail')]

    map_tag = soup.find('div', id='googleMapSlider')
    latitude = map_tag['data-cur_lat'] if map_tag and 'data-cur_lat' in map_tag.attrs else None
    longitude = map_tag['data-cur_long'] if map_tag and 'data-cur_long' in map_tag.attrs else None

    area = characteristics.get("Property Size", "-") if property_size == '-' else property_size

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

# Function to scrape data from start_page to end_page for a given base URL
def scrape_data_for_url(base_url, start_page=1, end_page=30):
    all_property_urls = []
    page = start_page

    while end_page is None or page <= end_page:
        property_urls = scrape_property_urls(base_url, page)
        if not property_urls:
            break
        all_property_urls.extend(property_urls)
        page += 1

    print(f"Found {len(all_property_urls)} property URLs from page {start_page} to {end_page}")

    all_properties = []
    for property_url in all_property_urls:
        print(f"Scraping property details from {property_url}...")
        property_details = scrape_property_details(property_url)
        all_properties.append(property_details)

    # Ensure the 'artifacts' directory exists
    os.makedirs('artifacts', exist_ok=True)

    # Save to Excel in the 'artifacts' folder
    base_url_cleaned = re.sub(r'[^a-zA-Z0-9]', '_', base_url.strip('/').replace('https://', ''))[:15]
    output_file = f"artifacts/{base_url_cleaned}_p{start_page}_to_p{end_page}.xlsx"
    df = pd.DataFrame(all_properties)
    df.to_excel(output_file, index=False)
    print(f"Data saved to {output_file}")

# Array of base URLs to scrape with specified start and end pages
base_urls = [
    ('https://boahiyaa.com/advanced-search/?geolocation_search=&geolocation_lat=&geolocation_long=&filter_search_type%5B%5D=&filter_search_action%5B%5D=&property_status=&submit=Search&elementor_form_id=21142', 1, 5),
]

# Loop through all base URLs and scrape data within the specified page range
for base_url, start_page, end_page in base_urls:
    scrape_data_for_url(base_url, start_page, end_page)
