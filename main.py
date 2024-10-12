import os
import requests
from bs4 import BeautifulSoup
import json
import pandas as pd
from geopy.geocoders import Nominatim

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.3'
}

# Create an output directory to store the Excel files
output_dir = 'output'
if not os.path.exists(output_dir):
    os.makedirs(output_dir)

def get_lat_lon(address):
    geolocator = Nominatim(user_agent="my_geocoder_app")
    
    try:
        location = geolocator.geocode(address)
        if location:
            print(f"Geocoded {address}: (Lat: {location.latitude}, Lon: {location.longitude})")
            return location.latitude, location.longitude
        else:
            print(f"Geocoding failed for {address}")
            return None, None
    except GeocoderTimedOut:
        # Retry once in case of a timeout
        time.sleep(2)
        return get_lat_lon(address)  # Recursion to retry once
    except Exception as e:
        print(f"Error geocoding {address}: {e}")
        return None, None
    finally:
        # Delay to avoid hitting rate limits
        time.sleep(1) 

def get_property_urls(base_url):
    property_urls = []
    page = 1

    while True:
        print(f"Scraping page {page} for {base_url}")

        if '?' in base_url:
            current_url = f"{base_url}&page={page}"
        else:
            current_url = f"{base_url}?page={page}"

        response = requests.get(current_url, headers=headers)

        if response.status_code != 200:
            print(f"Failed to retrieve page {page} from {current_url}, status code: {response.status_code}")
            break

        soup = BeautifulSoup(response.content, 'html.parser')

        page_property_urls = ['https://ci.coinafrique.com' + link.get('href') for link in soup.find_all('a', class_='card-image ad__card-image waves-block waves-light')]

        if not page_property_urls:
            print(f"No more property URLs found on page {page}. Stopping.")
            break

        property_urls.extend(page_property_urls)
        print(f"Collected {len(page_property_urls)} property URLs from page {page}")

        page += 1

    print(f"Total property URLs collected: {len(property_urls)}")
    return property_urls

def scrape_property_data(url):
    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        print(f"Failed to retrieve property data from {url}, status code: {response.status_code}")
        return None
    soup = BeautifulSoup(response.content, 'html.parser')

    try:
        name = soup.find('meta', attrs={'name': 'title'})['content'].strip()
    except AttributeError:
        name = None

    try:
        description_div = soup.find('div', class_='ad__info__box ad__info__box-descriptions')
        description = description_div.find_all('p')[1].text.strip()
    except (AttributeError, IndexError):
        description = None

    try:
        address_tag = soup.find('span', class_='valign-wrapper', attrs={'data-address': True})
        address = address_tag['data-address'].strip() if address_tag else None
    except AttributeError:
        address = None

    latitude, longitude = None, None
    if address:
        latitude, longitude = get_lat_lon(address)

    try:
        price = soup.find('p', class_='price').text.strip()
    except AttributeError:
        price = None

    try:
        characteristics = {}
        characteristic_items = soup.select('.details-characteristics ul li')
        for item in characteristic_items:
            label = item.find_all('span')[0].text.strip()
            value = item.find_all('span', class_='qt')[0].text.strip()
            characteristics[label] = value
    except AttributeError:
        characteristics = None

    try:
        area = next((value for key, value in characteristics.items() if 'Superficie' in key), None)
    except AttributeError:
        area = None

    try:
        ad_details = soup.find('div', id='ad-details')
        ad_data = json.loads(ad_details['data-ad'])
        property_type = ad_data['category']['name']
    except (AttributeError, KeyError, json.JSONDecodeError):
        property_type = None

    try:
        if "location" in name.lower():
            transaction_type = "rent"
        else:
            transaction_type = "buy"
    except AttributeError:
        transaction_type = None

    property_data = {
        'name': name,
        'address': address,
        'price': price,
        'area': area,
        'description': description,
        'latitude': latitude,
        'longitude': longitude,
        'property_type': property_type,
        'transaction_type': transaction_type,
        'property_url': url,
        'characteristics': characteristics
    }

    print(property_data)

    return property_data

def scrape_multiple_urls(urls):
    for base_url in urls:
        property_urls = get_property_urls(base_url)

        properties_data = []
        for index, property_url in enumerate(property_urls):
            print(f"Scraping property {index + 1} of {len(property_urls)} from {base_url}")
            data = scrape_property_data(property_url)
            if data:
                properties_data.append(data)

        df = pd.DataFrame(properties_data)
        excel_file_name = os.path.join(output_dir, f"{base_url.replace('https://', '').replace('/', '_').replace('?', '_').replace('&', '_').replace('=', '_')}.xlsx")
        df.to_excel(excel_file_name, index=False, sheet_name='Properties')

        print(f"Data from {base_url} saved to {excel_file_name}")

urls = [
    "https://ci.coinafrique.com/search?sort_by=last&category=14&price_min=10000&price_max=150000&is_pro=1"
]

scrape_multiple_urls(urls)
