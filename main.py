import requests
from bs4 import BeautifulSoup
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderServiceError
import logging
import pandas as pd
from urllib.parse import urlparse
import os

# Create session
session = requests.Session()
session.cookies.set('SESSION', '1f7c8fa12ffd405e~866b242d-587e-4ec1-a421-b72cb909d12c', domain='www.idealista.com')
session.cookies.set('contact866b242d-587e-4ec1-a421-b72cb909d12c', "{'maxNumberContactsAllow':10}", domain='www.idealista.com')
session.cookies.set('datadome', 'USbG0q5kyFe3vsqkR5071Lw0loDqUwQLGK9LyG7mYJHSd5BPQHCF2UrFRQYBRuZgeYbjLXlvKKyND87EpjvQtlvAz4WgmWis01~a~luEyjcKw9q4wyiK_vpBjkjJg_Ws', domain='www.idealista.com')
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/93.0.4577.63 Safari/537.36",
    "Accept-Encoding": "gzip, deflate",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "DNT": "1",
    "Connection": "close",
    "Upgrade-Insecure-Requests": "1"
}

def get_lat_lon_from_address(address):
    geolocator = Nominatim(user_agent="username")
    try:
        location = geolocator.geocode(address, timeout=10)
        if location:
            return location.latitude, location.longitude
        else:
            return None, None
    except (GeocoderTimedOut, GeocoderServiceError) as e:
        print(f"Error: {e}")
        return None, None

# Function to get all relevant anchor tags within a page range
def get_anchor_tags(url, start_page=1, end_page=None):
    links = []
    page_number = start_page
    while url and (end_page is None or page_number <= end_page):
        r = session.get(url, headers=headers)
        if r.status_code == 200:
            soup = BeautifulSoup(r.content, "lxml")
            anchor_tags = soup.find_all('a', class_='item-link')
            page_links = []
            for tag in anchor_tags:
                href = tag.get('href')
                if not href.startswith('http'):
                    href = 'https://www.idealista.com' + href
                page_links.append({'href': href})
            links.extend(page_links)
            print(f"Page {page_number} - Number of anchor tags: {len(page_links)}")

            # Find the next page URL
            next_page_tag = soup.find('li', class_='next')
            if next_page_tag:
                next_page_link = next_page_tag.find('a')
                if next_page_link and 'href' in next_page_link.attrs:
                    url = next_page_link['href']
                    if not url.startswith('http'):
                        url = 'https://www.idealista.com' + url
                else:
                    url = None
            else:
                url = None

            page_number += 1
        else:
            print(f"Failed to retrieve the page, status code: {r.status_code}")
            break
    return links

# Function to determine the transaction type
def get_transaction_type(name):
    rent_keywords = ["rent", "alquiler"]
    buy_keywords = ["buy", "sale", "venta"]
    
    for keyword in rent_keywords:
        if keyword in name.lower():
            return "rent"
    
    for keyword in buy_keywords:
        if keyword in name.lower():
            return "buy"
    
    return "unknown"

# Function to determine the property type
def get_property_type(start_url):
    property_types = {
        "new construction": ["new construction", "obra nueva","Obra nueva"],
        "housing": ["housing", "viviendas","Viviendas","vivienda","Vivienda"],
        "offices": ["offices", "oficinas","oficina","Oficina","office","offices"],
        "premises or warehouses": ["premises or warehouses", "locales o naves","locales o nave","Locales o naves","Local","locale","locales"],
        "garage": ["garage", "garages", "garajes","garaje"],
        "land": ["land", "terrenos","terreno"],
        "storerooms": ["storeroom", "storerooms"],
        "building": ["building", "buildings", "edificios","edificio"],
        "new home": ["new home"],
        "home": ["home"],
        "room": ["room", "Habitación","habitación "],
        "commercial property": ["commercial property"],
        "flat / apartment": ["flat", "apartment"],
        "storage room": ["storage room","Trasteros","Trastero","trastero","trasteros"]
    }
    for property_type, keywords in property_types.items():
        for keyword in keywords:
            if keyword.lower() in start_url.lower():
                return property_type

    return "unknown"

# Function to get property type from URL keywords
def get_property_type_from_url(base_url):
    keywords = {
        "viviendas": "housing",
        "oficinas": "offices",
        "locales o naves": "premises or warehouses",
        "traspasos": "transfers",
        "garajes": "garage",
        "terrenos": "land",
        "trasteros": "storerooms",
        "edificios": "building"
    }
    for keyword, property_type in keywords.items():
        if keyword in base_url:
            return property_type
    return "unknown"

def get_transaction_type_from_url(base_url):
    if "venta" in base_url:
        return "sale"
    elif "alquiler" in base_url:
        return "rent"
    return "unknown"

# Function to get the property details from the property URL
def get_property_details(property_url, transaction_type, property_type):
    r = session.get(property_url, headers=headers)
    if r.status_code == 200:
        soup = BeautifulSoup(r.content, "lxml")
        
        # Name
        name_tag = soup.find('span', class_='main-info__title-main')
        name = name_tag.text.strip() if name_tag else None
        
        # Address
        address_tag = soup.find('span', class_='main-info__title-minor')
        address = address_tag.text.strip() if address_tag else None
        
        # Price
        price_tag = soup.find('strong', class_='price')
        price = price_tag.text.strip() if price_tag else None
        
        # Description
        description = None
        comment_tag = soup.find('div', class_='comment')
        if comment_tag:
            description_paragraph = comment_tag.find('p')
            if description_paragraph:
                description = description_paragraph.get_text(separator="\n").strip()  
        
        # Properties
        properties_tag = soup.find('div', class_='details-property')
        properties = []
        if properties_tag:
            for ul in properties_tag.find_all('ul'):
                for li in ul.find_all('li'):
                    properties.append(li.text.strip())

        latitude, longitude = (None, None)

        # Geocode the address
        if address:
            latitude, longitude = get_lat_lon_from_address(address)
            if not (latitude and longitude):
                primary_location = address.split(",")[0].strip()
                latitude, longitude = get_lat_lon_from_address(primary_location)
            if not (latitude and longitude) and len(address.split(",")) > 1:
                secondary_location = address.split(",")[1].strip()
                latitude, longitude = get_lat_lon_from_address(secondary_location)

        # Features
        features = []
        features_tag = soup.find('div', class_='info-features')
        if features_tag:
            for span in features_tag.find_all('span'):
                features.append(span.text.strip())

        characteristics = []
        characteristics_tags = soup.find_all('div', class_='details-property-feature-one')
        if len(characteristics_tags) > 1:  # Ensure there's a second div
            for li in characteristics_tags[1].find_all('li'):
                characteristic = li.text.strip()
                characteristics.append(characteristic)
   

        # Area and characteristics
        area = '-'
        if "m²" in features[0]:
            area = features[0]
        return {
            'url': property_url,
            'name': name,
            'address': address,
            'price': price,
            'area': area,
            'description': description,
            "characteristics": characteristics,
            'properties': properties,
            "Features": features,
            'transaction_type': transaction_type,
            'property_type': property_type,
            'latitude': latitude,
            'longitude': longitude
        }
    else:
        print(f"Failed to retrieve the property page, status code: {r.status_code}")
        return None

def get_base_url(url):
    parsed_url = urlparse(url)
    return parsed_url.netloc

if __name__ == "__main__":
    start_urls = [
       'https://www.idealista.com/buscar/venta-viviendas/con-precio-hasta_80000/spain/',
        # Add more URLs as needed
    ]
    
    # Specify start and end pages here
    start_page = 1
    end_page = 60

    output_directory = "artifacts"
    if not os.path.exists(output_directory):
        os.makedirs(output_directory)

    for start_url in start_urls:
        base_url = get_base_url(start_url)
        transaction_type = get_transaction_type_from_url(start_url)
        print("transaction type: ", transaction_type)
        property_type = get_property_type_from_url(start_url)
        print("property type: ", property_type)
        
        # Get all links within the specified page range
        all_links = get_anchor_tags(start_url, start_page, end_page)
        print(f"Total number of links for {base_url}: {len(all_links)}")
        
        data = []
        for link in all_links:
            details = get_property_details(link['href'], transaction_type, property_type)
            print(details)
            if details:
                data.append(details)
            else:
                print(f"Property URL: {link['href']} - Details: Not Found")
        
        # Save data to Excel
        df = pd.DataFrame(data)
        sanitized_url = start_url.replace('https://', '').replace('/', '_').replace('.', '_')
        excel_file_path = os.path.join(output_directory, f'{sanitized_url}.xlsx')
        df.to_excel(excel_file_path, index=False)
        print(f"Data saved to {excel_file_path}")
