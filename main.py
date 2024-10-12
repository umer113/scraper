import requests
import json
from bs4 import BeautifulSoup
from urllib.parse import urljoin, quote
import pandas as pd
import time
import logging
import re

# Configure logging
logging.basicConfig(filename='scraper.log', level=logging.ERROR, 
                    format='%(asctime)s %(levelname)s %(message)s')

# Function to fetch and parse a webpage with retry logic
def fetch_page(url, retries=3):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0"
    }
    for attempt in range(retries):
        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            return BeautifulSoup(response.content, 'html.parser')
        except requests.exceptions.HTTPError as e:
            logging.error(f"HTTPError: {e} for URL: {url}")
            if attempt < retries - 1:
                print(f"HTTPError: {e}, retrying ({attempt + 1}/{retries})...")
                time.sleep(2)  # Wait before retrying
            else:
                print(f"Failed to fetch {url} after {retries} attempts.")
                return None
        except requests.exceptions.RequestException as e:
            logging.error(f"RequestException: {e} for URL: {url}")
            return None

def extract_lat_long(url):
    try:
        response = requests.get(url)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, "html.parser")
            script_tag = soup.find('script', id="__NEXT_DATA__", type="application/json")

            # Ensure the script_tag exists and has the correct structure
            if not script_tag or not script_tag.string:
                return '-', '-'

            json_data = json.loads(script_tag.string)

            listing_id_match = re.search(r'-(\d+)/$', url)
            if listing_id_match:
                listing_id = listing_id_match.group(1)
            else:
                return '-', '-'

            listing_key = f'ListingDetail:{listing_id}'

            # Check if apolloState and listing_key exist in json_data
            apollo_state = json_data.get('props', {}).get('apolloState', {})
            if not apollo_state:
                logging.error(f"Missing 'apolloState' in JSON for URL: {url}")
                return '-', '-'

            if listing_key not in apollo_state:
                logging.error(f"Missing 'listing_key' ({listing_key}) in apolloState for URL: {url}")
                return '-', '-'

            geo_location_ref = apollo_state[listing_key].get('geoLocation', {}).get('id', None)

            if not geo_location_ref:
                logging.error(f"Missing 'geoLocation' for listing key {listing_key} in URL: {url}")
                return '-', '-'

            geo_location_data = apollo_state.get(geo_location_ref, None)
            if geo_location_data:
                latitude = geo_location_data.get('latitude', '-')
                longitude = geo_location_data.get('longitude', '-')
                return latitude, longitude
            else:
                logging.error(f"Missing geo location data for reference {geo_location_ref} in URL: {url}")
                return '-', '-'

        else:
            logging.error(f"Failed to fetch page for URL: {url}, status code: {response.status_code}")
            return '-', '-'

    except Exception as e:
        logging.error(f"Error in extract_lat_long for URL: {url}: {str(e)}")
        return '-', '-'



# Function to extract property details
def extract_property_details(soup, transaction_type, property_url):
    details = {}
    details['name'] = soup.select_one('h1.display-address').text if soup.select_one('h1.display-address') else None
    details['price'] = soup.select_one('div.property-price').text.strip() if soup.select_one('div.property-price') else None
    details['address'] = soup.select_one('div.lbxu17-1.description-address').text if soup.select_one('div.lbxu17-1.description-address') else None
    details['description'] = soup.select_one('pre.property-description').text.strip() if soup.select_one('pre.property-description') else None
    details['area'] = None
    details['property_type'] = soup.select_one('div.feature-item:last-child').text.strip() if soup.select_one('div.feature-item:last-child') else None
    details['transaction_type'] = transaction_type
    details['property_url'] = property_url

    # Scrape latitude and longitude
    latitude, longitude = extract_lat_long(property_url)
    details['latitude'] = latitude
    details['longitude'] = longitude

    # Initialize a dictionary for characteristics
    characteristics = {}
    
    # Extract characteristics as key-value pairs
    characteristic_elements = soup.select('div.sc-12iqlu8-0.hMXWVZ')
    for element in characteristic_elements:
        key = element.select_one('div.basicInfoKey').text.strip() if element.select_one('div.basicInfoKey') else None
        value = element.select_one('div.basicInfoValue').text.strip() if element.select_one('div.basicInfoValue') else None
        if key and value:
            characteristics[key] = value
    
    # Add characteristics to details
    details['characteristics'] = characteristics
    print(details['characteristics'])

    # area
    area_element = soup.find('div', {'class': 'props-name'}, text='Floor Area')
    if area_element:
        details['area'] = area_element.find_next('div', {'class': 'props-value'}).text.strip()
    else:
        details['area'] = None

    return details

# Function to check if there is a next page
def has_next_page(soup):
    next_button = soup.select_one('li.ant-pagination-next a')
    return bool(next_button)

# Function to extract property URLs and transaction types from a page
def extract_property_urls_and_transactions(soup, base_url):
    properties = []
    listings = soup.select('div.sc-1dun5hk-0.cOiOrj > a')
    for listing in listings:
        url = urljoin(base_url, listing['href'])
        transaction_type_div = soup.select_one('div.sc-1mgu4iw-2.Wxcys.channel')
        transaction_type = transaction_type_div.text.strip() if transaction_type_div else 'Unknown'
        properties.append({'url': url, 'transaction_type': transaction_type})
    return properties

# Function to sanitize the URL to make it a valid filename
def sanitize_url_for_filename(url):
    return quote(url, safe='')

# List of base URLs
base_urls = [
    "https://www.realtor.com/international/jm?maxprice=100000",
]

# Loop through each base URL
for base_url in base_urls:
    current_page_num = 1
    all_properties = []

    while True:
        # Construct the pagination URL dynamically by injecting the page number at the right place
        if current_page_num == 1:
            current_url = base_url
        else:
            current_url = f"{base_url}&page={current_page_num}"
        
        # Fetch and parse the current page
        soup = fetch_page(current_url)
        if soup is None:
            break
        
        page_properties = extract_property_urls_and_transactions(soup, base_url)
        all_properties.extend(page_properties)
        
        print(f"Number of properties on page {current_page_num} for {current_url}: {len(page_properties)}")
        
        # Check if there is a next page
        if not has_next_page(soup):
            break
        
        current_page_num += 1

    print(f"Total number of properties collected for {base_url}: {len(all_properties)}")

    property_details_list = []
    for property in all_properties:
        property_soup = fetch_page(property['url'])
        if property_soup:
            details = extract_property_details(property_soup, property['transaction_type'], property['url'])
            print(details)
            property_details_list.append(details)
            print(f"Extracted details for URL: {property['url']}")
        else:
            print(f"Skipping URL: {property['url']} due to a fetch error.")

    print(f"Total properties scraped for {base_url}: {len(property_details_list)}")

    # Save to an Excel file using the sanitized URL as filename
    df = pd.DataFrame(property_details_list)
    sanitized_filename = sanitize_url_for_filename(base_url) + ".xlsx"
    df.to_excel(sanitized_filename, index=False)
    print(f"Data saved to {sanitized_filename}")
