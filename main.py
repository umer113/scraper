import os
import requests
from bs4 import BeautifulSoup
import json
import pandas as pd
import re
import math

# Function to scrape property details from a property URL
def scrape_property_details(property_url):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36"
    }
    response = requests.get(property_url, headers=headers)
    soup = BeautifulSoup(response.content, 'html.parser')
    
    property_data = {}
    property_data['URL'] = property_url

    # Scraping the property name from <meta property="og:title">
    title_meta = soup.find('meta', property="og:title")
    if title_meta:
        property_data['Name'] = title_meta['content']

    # Scraping the address
    address_div = soup.find('div', class_='e4fd45f0')
    if address_div:
        property_data['Address'] = address_div.text.strip()
    else:
        property_data['Address'] = None
    
    # Scraping the price
    price_span = soup.find('span', {'aria-label': 'Price'})
    price = price_span.text if price_span else None
    property_data['Price'] = price

    # Scraping the description
    description_span = soup.find('span', class_='_3547dac9')
    if description_span:
        property_data['Description'] = description_span.text.strip()
    else:
        property_data['Description'] = None

    # Scraping property characteristics (stored as key-value pairs)
    property_info = soup.find('ul', class_='_3dc8d08d')
    if property_info:
        info_items = property_info.find_all('li')
        characteristics = {}
        for item in info_items:
            label = item.find('span', class_='ed0db22a').text.strip()
            value = item.find('span', class_='_2fdf7fc5').text.strip()
            characteristics[label] = value
        property_data['Characteristics'] = characteristics


    property_info = soup.find('ul', class_='_3dc8d08d')
    if property_info:
        info_items = property_info.find_all('li')
        for item in info_items:
            label = item.find('span', class_='ed0db22a').text.strip()
            value = item.find('span', class_='_2fdf7fc5').text.strip()
            if label == "Type":
                property_data['Property Type'] = value
            elif label == "Purpose":
                property_data['Transaction Type'] = value

    try:
        details_div = soup.find('div', class_='_14f36d85')
        if details_div:
            details_spans = details_div.find_all('span', class_='_783ab618')
            for detail in details_spans:
                label = detail['aria-label']
                value = detail.find('span', class_='_140e6903').text.strip()
                if label == 'Beds':
                    property_data['Beds'] = value
                elif label == 'Baths':
                    property_data['Baths'] = value
                elif label == 'Area':
                    property_data['Area'] = value
    except Exception as e:
        print(f"Error scraping Beds, Baths, and Area: {e}")


    # Scraping latitude and longitude from the second JSON-LD script tag
    script_tags = soup.find_all('script', type="application/ld+json")
    if len(script_tags) >= 2:  # Check if there are at least two script tags
        second_script_tag = script_tags[1]  # Index 1 for the second tag
        try:
            json_data = json.loads(second_script_tag.string)
            geo = json_data.get('geo', {})
            property_data['Latitude'] = geo.get('latitude')
            property_data['Longitude'] = geo.get('longitude')
        except json.JSONDecodeError:
            print("Error parsing JSON data from the second script tag")
    else:
        print("Not enough JSON-LD script tags found")

    return property_data

# Function to scrape total listings and property URLs from a single page
def scrape_page(url):
    base_url = "https://www.bayut.jo"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36"
    }
    response = requests.get(url, headers=headers)
    soup = BeautifulSoup(response.content, 'html.parser')
    
    property_urls = set()

    property_links = soup.find_all('a', class_='d40f2294')
    for link in property_links:
        full_url = base_url + link['href']
        property_urls.add(full_url)
    
    summary_span = soup.find('span', class_=re.compile(r'_71ab91b9'))
    total_listings = None
    if summary_span:
        summary_text = summary_span.text.strip()
        match = re.search(r'of\s+([\d,]+)', summary_text)
        if match:
            total_listings = int(match.group(1).replace(',', ''))

    return property_urls, total_listings

# Function to generate pagination URLs by inserting 'page-{number}' after the 6th '/'
def generate_pagination_urls(base_url, total_pages):
    url_parts = base_url.split('/')
    urls = [base_url]  # First page URL
    
    for page in range(2, total_pages + 1):
        # Insert 'page-{page}' after the 6th '/' and rejoin the URL
        pagination_url = '/'.join(url_parts[:6]) + f'/page-{page}/' + '/'.join(url_parts[6:])
        urls.append(pagination_url)
    
    return urls

# Main function to scrape multiple pages
def main(urls):
    output_dir = "output"
    
    # Ensure the output directory exists
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    for url in urls:
        count = 1
        all_properties = []
        print(f"Scraping property URLs from: {url}")
        
        property_urls, total_listings = scrape_page(url)
        if total_listings is None:
            print("Could not determine total listings.")
            continue

        print(f"Total listings found: {total_listings}")
        
        # Calculate total number of pages (24 listings per page)
        total_pages = math.ceil(total_listings / 24)
        print(f"Total pages: {total_pages}")
        
        # Generate pagination URLs
        pagination_urls = generate_pagination_urls(url, total_pages)
        
        for page_url in pagination_urls:
            print(f"Scraping page: {page_url}")
            page_property_urls, _ = scrape_page(page_url)
            property_urls.update(page_property_urls)
        
        print(f"Total property URLs collected: {len(property_urls)}")

        for property_url in property_urls:
            print(f"Scraping details from property: {property_url}")
            property_details = scrape_property_details(property_url)
            print(property_details)
            all_properties.append(property_details)
            print(count)
            count+=1
        
        if all_properties:
            sanitized_filename = re.sub(r'[\\/*?:"<>|]', "_", url.replace('https://', '').replace('/', '_'))
            filename = f"{output_dir}/{sanitized_filename}.xlsx"
            df = pd.DataFrame(all_properties)
            df.to_excel(filename, index=False)
            print(f"Saved all data to {filename}")

# Example of usage with multiple URLs
urls = [
 "https://www.bayut.jo/en/jordan/apartments-for-rent/"
]

main(urls)
