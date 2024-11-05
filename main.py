import os
import requests
from bs4 import BeautifulSoup
import pandas as pd
from geopy.geocoders import Nominatim

# Function to scrape the property URLs from each base URL
def scrape_property_urls(base_url):
    page_num = 1
    property_links = set()
    
    while True:
        url = f"{base_url}?&page={page_num}"
        print(f"Scraping page {page_num}: {url}")
        
        response = requests.get(url)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        div_blocks = soup.find_all('div', class_='serp__block-left')
        if not div_blocks:
            print("No more property divs found. Stopping.")
            break
        
        page_links = set()
        for div in div_blocks:
            a_tag = div.find('a', class_='click_and_track_detail_ads_link')
            if a_tag:
                link = a_tag.get('href')
                if link:
                    if link.startswith("http"):
                        full_link = link
                    else:
                        full_link = "https://www.shweproperty.com" + link
                    page_links.add(full_link)
        
        property_links.update(page_links)
        print(f"Page {page_num} property URLs count: {len(page_links)}")
        page_num += 1

    return list(property_links)

# Function to scrape details from a property URL
def scrape_property_details(url,transaction_type):
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # Scrape name
    name = soup.find('meta', property='og:title').get('content') if soup.find('meta', property='og:title') else None
    description = soup.find('div', class_='property__about-body').get_text(separator="\n").strip() if soup.find('div', class_='property__about-body') else None
    address_divs = soup.find_all('p', class_='property__about-title')
    address = address_divs[1].get_text().strip() if len(address_divs) > 1 else None
    sub_address = address.split(",")[-1].strip() if address and "," in address else None
    price = soup.find('p', class_='property__about-subtitle').find('span').get_text().strip() if soup.find('p', class_='property__about-subtitle') and soup.find('p', class_='property__about-subtitle').find('span') else None
    
    characteristics = {}
    details_div = soup.find('div', class_='property__details')
    if details_div:
        for li in details_div.find_all('li'):
            label = li.find('p').get_text().strip() if li.find('p') else None
            value = li.find('span').get_text().strip() if li.find('span') else None
            if label and value:
                characteristics[label] = value
    
    property_type = characteristics.get("Type", None)
    area = characteristics.get("Area", None)
    features = [li.get_text().strip() for li in soup.find('div', class_='property__special').find('ul').find_all('li')] if soup.find('div', class_='property__special') else []
    
    geolocator = Nominatim(user_agent="YourAppName")
    location = geolocator.geocode(sub_address, timeout=10) if sub_address else None
    latitude = location.latitude if location else None
    longitude = location.longitude if location else None
    
    return {
        'URL': url,
        'Name': name,
        'Description': description,
        'Address': address,
        'Price': price,
        'Characteristics': characteristics,
        'Features': features,
        'Area': area,
        'Property Type': property_type,
        'Transaction Type': transaction_type,
        'Latitude': latitude,
        'Longitude': longitude
    }

# Main function to handle scraping multiple base URLs
def scrape_multiple_urls(base_urls):
    os.makedirs("artifacts", exist_ok=True)  # Ensure the artifacts folder exists

    for base_url in base_urls:
        print(f"Scraping base URL: {base_url}")
        transaction_type = ''
        if "buy" in base_url:
            transaction_type = "buy"
        elif "rent" in base_url:
            transaction_type = "rent"
            
        property_urls = scrape_property_urls(base_url)
        scraped_data = []
        
        for property_url in property_urls:
            print(f"Scraping property: {property_url}")
            property_data = scrape_property_details(property_url,transaction_type)
            print(property_data)
            scraped_data.append(property_data)
        
        # Convert data to DataFrame and save to Excel in artifacts folder
        df = pd.DataFrame(scraped_data)
        file_name = "artifacts/" + base_url.replace("https://", "").replace("/", "_") + ".xlsx"
        df.to_excel(file_name, index=False)
        print(f"Data saved to {file_name}")

# Example usage with multiple URLs
base_urls = [
    "https://www.shweproperty.com/en/buy-property",
]

scrape_multiple_urls(base_urls)
