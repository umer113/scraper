import requests
from bs4 import BeautifulSoup
import math
import re
import pandas as pd
from geopy.geocoders import Nominatim
from openpyxl import Workbook

def extract_property_data(property_url):
    details = {}
    response = requests.get(property_url)
    response.raise_for_status()
    soup = BeautifulSoup(response.content, 'html.parser')
    
    # Extract property name
    name_tag = soup.find('meta', attrs={'name': 'twitter:title'})
    name = name_tag['content'] if name_tag else None
    
    # Extract address
    address_tag = soup.find('h1', class_='property-address')
    address = address_tag.text.strip() if address_tag else None
    
    # Extract price
    price_tag = soup.find('h2', class_='property-price')
    price = price_tag.text.strip() if price_tag else None
    
    # Extract description
    description_tag = soup.find('div', class_='description listing-read-more')
    description = description_tag.text.strip() if description_tag else None
    
    # Extract characteristics
    characteristics = {}
    details_section = soup.find('div', class_='details row')
    if details_section:
        for li in details_section.find_all('li'):
            try:
                key, value = li.text.split(':')
                characteristics[key.strip()] = value.strip()
            except ValueError:
                continue
    
    # Extract property type
    property_type = characteristics.get('Property Type', None)
    area = characteristics.get("Land Area",None)
    
    # Determine transaction type from URL
    transaction_type = 'sale' if 'sale' in property_url else 'rent'
    
    # Get latitude and longitude using geopy
    geolocator = Nominatim(user_agent="property_scraper")
    location = geolocator.geocode(address) if address else None
    latitude = location.latitude if location else None
    longitude = location.longitude if location else None

    details = {
        'Name': name,
        'Address': address,
        'Price': price,
        'Area': area,
        'Description': description,
        'Property Type': property_type,
        'Transaction Type': transaction_type,
        'Characteristics': characteristics,
        'Latitude': latitude,
        'Longitude': longitude,
        'URL': property_url
    }

    print(details)
    
    return details

def clean_filename(base_url):
    # Replace invalid characters with underscores
    valid_filename = re.sub(r'[\/:*?"<>|]', '_', base_url)
    return valid_filename

def save_to_excel(data, filename):
    df = pd.DataFrame(data)
    df.to_excel(filename, index=False)

# Function to extract property URLs from a page
def extract_property_urls(soup):
    property_urls = []
    listings = soup.find_all('div', class_='listing-card residential None')
    for listing in listings:
        a_tag = listing.find('a')
        if a_tag and 'href' in a_tag.attrs:
            property_url = domain + a_tag['href']
            property_urls.append(property_url)
    return property_urls

# Scraping logic in a function
def scrape_properties(base_urls):
    for base_url in base_urls:
        # Send a GET request to the first page to find the total number of properties
        response = requests.get(base_url + "1")
        response.raise_for_status()  # Check that the request was successful
        soup = BeautifulSoup(response.content, 'html.parser')

        # Find the specific div containing the text to extract the number of properties
        search_result = soup.find('div', class_='search-result-description')

        if search_result:
            match = re.search(r'Found (\d+) (Residential|Rental)', search_result.text)
            if match:
                number_of_properties = int(match.group(1))  # Convert to integer
                property_type = match.group(2)  # Capture the property type (Residential or Rental)
                print(f"Number of {property_type} Properties: {number_of_properties}")
            else:
                print("Number not found in the text.")
        else:
            print("Search result description not found on the page.")

        # Calculate total pages
        properties_per_page = 10
        total_pages = math.ceil(number_of_properties / properties_per_page)  # Division and ceiling
        print(f"Total pages: {total_pages}")

        all_property_urls = []
        # Iterate through each page and scrape the property URLs
        for page in range(1, total_pages + 1):
            page_url = f"{base_url}#page-{page}"
            response = requests.get(page_url)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
            property_urls = extract_property_urls(soup)
            all_property_urls.extend(property_urls)
            print(f"Page {page}")

        # Extract details from each property URL and save them to Excel files
        all_property_data = []
        for property_url in all_property_urls:
            property_data = extract_property_data(property_url)
            all_property_data.append(property_data)

        file_name = clean_filename(base_url) + ".xlsx"
        save_to_excel(all_property_data, file_name)
        print(f"Data for properties from {base_url} saved to {file_name}")

if __name__ == "__main__":
    # Modify to accept multiple base URLs
    base_urls = [
        "https://www.property.com.fj/rent/?listing_type=lease&property_type=rental&order_by=relevance&is_certified=1&private_seller=1"
    ]
    domain = "https://www.property.com.fj/"
    scrape_properties(base_urls)
