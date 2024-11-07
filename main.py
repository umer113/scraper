import os
import requests
from bs4 import BeautifulSoup
import json
import pandas as pd

# Ensure the artifacts directory exists
os.makedirs("artifacts", exist_ok=True)

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

def get_property_urls(base_url):
    property_urls = []
    page = 1
    while True:
        print(f"Scraping page {page} for {base_url}")
        current_url = f"{base_url}?page={page}"
        response = requests.get(current_url, headers=headers)

        if response.status_code != 200:
            print(f"Failed to retrieve page {page}, status code: {response.status_code}")
            break

        soup = BeautifulSoup(response.content, 'html.parser')
        page_property_urls = ['https://cm.coinafrique.com' + link.get('href') for link in soup.find_all('a', class_='card-image ad__card-image waves-block waves-light')]
        if not page_property_urls:
            print(f"No more property URLs found on page {page}. Stopping.")
            break
        property_urls.extend(page_property_urls)
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
        description = description_div.find_all('p')[1].text.strip() if description_div else None
    except (AttributeError, IndexError):
        description = None

    try:
        address_tag = soup.find('span', class_='valign-wrapper', attrs={'data-address': True})
        address = address_tag['data-address'].strip() if address_tag else None
    except AttributeError:
        address = None

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
        transaction_type = "rent" if "location" in name.lower() else "buy"
    except AttributeError:
        transaction_type = None

    try:
        hidden_input = soup.find('input', attrs={'id': 'country'})
        hidden_value = hidden_input['value'] if hidden_input else '{}'
        hidden_data = json.loads(hidden_value)
        latitude = hidden_data.get('latitude', None)
        longitude = hidden_data.get('longitude', None)
    except (AttributeError, json.JSONDecodeError):
        latitude = None
        longitude = None

    return {
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

def scrape_multiple_urls(urls):
    for base_url in urls:
        property_urls = get_property_urls(base_url)
        properties_data = [scrape_property_data(url) for url in property_urls if scrape_property_data(url)]

        # Save data to Excel file in the artifacts directory
        df = pd.DataFrame(properties_data)
        excel_file_name = f"artifacts/{base_url.replace('https://', '').replace('/', '_').replace('?', '_').replace('&', '_').replace('=', '_')}.xlsx"
        df.to_excel(excel_file_name, index=False, sheet_name='Properties')

        print(f"Data from {base_url} saved to {excel_file_name}")

urls = ["https://cm.coinafrique.com/categorie/immobilier"]
scrape_multiple_urls(urls)
