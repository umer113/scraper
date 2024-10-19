from curl_cffi import requests
from bs4 import BeautifulSoup
import time
import re
import base64
import pandas as pd
import os

def delay(seconds):
    time.sleep(seconds)

# Set headers to mimic a real browser

headers = {
    "accept": "*/*",
    "accept-language": "en-US,en;q=0.9",
    "content-type": "application/json",
    "cookie": 'g_state={"i_p":1726649448322,"i_l":2}; sessionId=3c0eab74-05d4-4c5d-b410-6adc78341cda; cf_clearance=0rCTlK15Rku4UcxWWgYSt3PBplzNBpBgvY3Jgmk3GsM-1729350761-1.2.1.1-5oFM8J2GFbYRIkZiqArJ9vsGvseSkpxmOmV9vsRUifzYTNJr.xGTw.lbSCKH_wubwKM_4VxQT6p_W8DGc3Z_K1pFlXsShlb2CU0rzevIpDoFW.IK9a9cRbF._hckOUZdfweoaGG3lsJW1DSzoayJ0Y2aNFM2GLx08qUlsj43VEevetO4TPHFegILIw4JWSMZmnGQvO4_n7C2_siux9UpbMQCa4RxDcyj1ukBw3upyDLFXzHdCjlflCeB2G9EeREJZ4YLcrdTTywsNRlwmPgJigfDfYlL9BuY.s6dQHpGXLlD2dSjNss6.UEvJm2WlVUdmHotKTKwty2L7FJOxLEISpaXmaJx23Q6921W_CwbIzzkETge.CSvwB6wHLFxKWQ6QLlKPstqUIxBA.OaD7ADPQ; JSESSIONID=BB925B2CE2B791EC16BD70CA6020C6EA; __cf_bm=zuB18Ael.apJCR8CpbHSdF_IHZwNw2cQwBIlFtsM28I-1729350763-1.0.1.1-OONfyCZjXPyAgf9L7GSR2NTcxWDEGjDYUvDSZMlC7qSlq_GWw.F1qbN7WQHYCjouDlrOu.NXAkEhrtmBTaRjVDMRAzQ.JJItlqbycpxYPIk; _cfuvid=vL96C4wnVl5.oPOsXXpNJ3EV3Y2wp5kHpf6vx5104c0-1729350763750-0.0.1.1-604800000',
    "priority": "u=1, i",
    "referer": "https://www.zonaprop.com.ar/departamentos-venta-menos-45000-dolar.html",
    "sec-ch-ua": '"Chromium";v="130", "Microsoft Edge";v="130", "Not?A_Brand";v="99"',
    "sec-ch-ua-arch": "",
    "sec-ch-ua-bitness": "64",
    "sec-ch-ua-full-version": "130.0.2849.46",
    "sec-ch-ua-full-version-list": '"Chromium";v="130.0.6723.59", "Microsoft Edge";v="130.0.2849.46", "Not?A_Brand";v="99.0.0.0"',
    "sec-ch-ua-mobile": "?1",
    "sec-ch-ua-model": "Nexus 5",
    "sec-ch-ua-platform": "Android",
    "sec-ch-ua-platform-version": "6.0",
    "sec-fetch-dest": "empty",
    "sec-fetch-mode": "cors",
    "sec-fetch-site": "same-origin",
    "user-agent": "Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Mobile Safari/537.36 Edg/130.0.0.0"
}
# Function to scrape property URLs from a page
def scrape_property_urls(soup):
    property_urls = []
    for h3 in soup.find_all('h3', {'data-qa': 'POSTING_CARD_DESCRIPTION'}):
        a_tag = h3.find('a')
        if a_tag and a_tag.get('href'):
            property_urls.append(a_tag['href'])
    return property_urls

# Function to get the next page URL
def get_next_page_url(soup):
    next_page = soup.find('a', {'data-qa': 'PAGING_NEXT'})
    if next_page and 'href' in next_page.attrs:
        return next_page['href']
    return None

# Function to extract page number from the URL
def extract_page_number(url):
    match = re.search(r'-pagina-(\d+)\.html', url)
    return int(match.group(1)) if match else 1

# Function to scrape the property details from a property page
def scrape_property_details(property_url):
    details = {}
    try:
        response = requests.get(property_url, headers=headers)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Scrape property name
            meta_title = soup.find('meta', property='og:title')
            if meta_title:
                details['name'] = meta_title['content']
            
            # Scrape property description
            meta_description = soup.find('meta', attrs={'name': 'description'})
            description = meta_description['content'] if meta_description else None

            if description:
                details['description'] = description.replace('<br>', ' ').replace('<br />', ' ').strip()

            transaction_tag = soup.find('span', class_='operation-type')
            if transaction_tag:
                transaction_type = transaction_tag.get_text(strip=True)
                details['transaction_type'] = transaction_type
            else:
                # If not found in the span, check the property URL for 'venta' (sale) or 'alquiler' (rent)
                if 'venta' in property_url:
                    details['transaction_type'] = 'venta'
                elif 'alquiler' in property_url:
                    details['transaction_type'] = 'alquiler'
                else:
                    # If not found in the URL, check the property name for 'venta' or 'alquiler'
                    if 'venta' in details.get('name', '').lower():
                        details['transaction_type'] = 'venta'
                    elif 'alquiler' in details.get('name', '').lower():
                        details['transaction_type'] = 'alquiler'
                    else:
                        # Check in the price-value div
                        price_tag = soup.find('div', class_='price-value')
                        if price_tag:
                            transaction_span = price_tag.find('span')
                            if transaction_span:
                                transaction_type = transaction_span.get_text(strip=True).lower()
                                if 'venta' in transaction_type:
                                    details['transaction_type'] = 'venta'
                                elif 'alquiler' in transaction_type:
                                    details['transaction_type'] = 'alquiler'
                                else:
                                    details['transaction_type'] = 'non-residential'
                        else:
                            details['transaction_type'] = 'non-residential'

            # Scrape property price
            prices = []

            # Find all price-item-container divs
            price_containers = soup.find_all('div', class_='price-item-container')

            # Loop through each container and extract transaction type and price
            for container in price_containers:
                # Find the span containing the transaction type (e.g., venta, alquiler)
                transaction_span = container.find('span')
                if transaction_span:
                    transaction_type = transaction_span.contents[0].strip()  # Get the first content (transaction type)
                    price_span = transaction_span.find('span')  # Find the nested span containing the price
                    if price_span:
                        price_value = price_span.get_text(strip=True)  # Extract the price text
                        prices.append(f"{transaction_type}: {price_value}")  # Store both transaction type and price
            # Scrape property address
            address_tag = soup.find('div', class_='section-location-property-classified')
            if address_tag:
                address_h4 = address_tag.find('h4')
                if address_h4:
                    details['address'] = address_h4.get_text(strip=True)
            
            # Scrape property type and area
            title_type = soup.find('h2', class_='title-type-sup-property')
            if title_type:
                title_text = title_type.get_text(strip=True)
                details['property_type'] = title_text.split('·')[0].strip()
                area_match = re.search(r'(\d+)\s?m²', title_text)
                if area_match:
                    details['area'] = area_match.group(1)

            # Scrape characteristics
            characteristics = {}
            features_section = soup.find('ul', id='section-icon-features-property')
            if features_section:
                for li in features_section.find_all('li', class_='icon-feature'):
                    icon_class = li.find('i')['class'][0].replace('icon-', '')
                    feature_text = li.get_text(strip=True)
                    # Clean up the wide spacing and newlines
                    cleaned_feature_text = re.sub(r'\s+', ' ', feature_text).strip()
                    characteristics[icon_class] = cleaned_feature_text

            details['characteristics'] = characteristics

            # Scrape property latitude and longitude
            map_lat_of = soup.find(string=re.compile(r'const mapLatOf'))
            map_lng_of = soup.find(string=re.compile(r'const mapLngOf'))
            if map_lat_of and map_lng_of:
                lat_encoded = re.search(r'\"(LT[^\"]+)\"', map_lat_of).group(1)
                lng_encoded = re.search(r'\"(LT[^\"]+)\"', map_lng_of).group(1)
                latitude = base64.b64decode(lat_encoded).decode('utf-8')
                longitude = base64.b64decode(lng_encoded).decode('utf-8')
                details['latitude'] = latitude
                details['longitude'] = longitude

            # Add the property URL
            details['url'] = property_url

        else:
            print(f"Failed to retrieve {property_url}. Status code: {response.status_code}")
    except Exception as e:
        print(f"An error occurred while scraping property details: {e}")
    return details

# Function to save data to an Excel file
def save_to_excel(data, start_url):
    # Create a DataFrame from the data
    df = pd.DataFrame(data)
    
    # Generate filename from the start URL
    filename = re.sub(r'\W+', '_', start_url.split('//')[-1].split('/')[0] + '_' + start_url.split('//')[-1].split('/')[-1]) + '.xlsx'
    
    # Ensure the output directory exists
    output_dir = 'output'
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    # Save DataFrame to an Excel file in the output directory
    filepath = os.path.join(output_dir, filename)
    df.to_excel(filepath, index=False)
    print(f"Data saved to {filepath}")

# Function to scrape properties from a list of start URLs
def scrape_properties_from_urls(start_urls):
    for start_url in start_urls:
        current_url = start_url
        all_property_details = []

        while current_url:
            try:
                # Make a request to the URL
                response = requests.get(current_url, headers=headers)
                if response.status_code == 200:
                    print(f"Scraping {current_url}")
                    soup = BeautifulSoup(response.text, 'html.parser')
                    
                    # Scrape property URLs
                    property_urls = scrape_property_urls(soup)
                    
                    # Print the page number and the total number of URLs found
                    page_number = extract_page_number(current_url)
                    print(f"Page Number: {page_number}")
                    print(f"Total URLs found on this page: {len(property_urls)}")
                    
                    # Scrape the details of each property
                    for url in property_urls:
                        if not url.startswith('http'):
                            url = f"https://www.zonaprop.com.ar{url}"
                        print(f"Scraping property at {url}")
                        property_details = scrape_property_details(url)
                        if property_details:
                            print(f"Property Details: {property_details}")
                            all_property_details.append(property_details)
                        else:
                            print("Property details not found.")
                    
                    # Get the next page URL
                    next_page_url = get_next_page_url(soup)
                    if next_page_url:
                        # Form the full URL if it's a relative path
                        if not next_page_url.startswith('http'):
                            next_page_url = f"https://www.zonaprop.com.ar{next_page_url}"
                        current_url = next_page_url
                        print(f"Next page: {current_url}")
                    else:
                        print("No more pages.")
                        current_url = None

                else:
                    print(f"Failed to retrieve {current_url}. Status code: {response.status_code}")
                    break

            except Exception as e:
                print(f"An error occurred: {e}")
                break
        
        # Save the scraped data to an Excel file
        save_to_excel(all_property_details, start_url)

# List of start URLs
start_urls = [

    'https://www.zonaprop.com.ar/departamentos-venta-menos-45000-dolar.html'
]

# Scrape properties from the list of start URLs
scrape_properties_from_urls(start_urls)
