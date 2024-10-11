import requests
from bs4 import BeautifulSoup
import math
import pandas as pd

# URL of the page to scrape
base_url = 'https://www.remax.sr/en/homes/homes-for-sale.html'

# Send a GET request to fetch the HTML content of the first page
response = requests.get(base_url)
soup = BeautifulSoup(response.text, 'html.parser')

# Find the total number of listings from the <h1> tag
total_listings_tag = soup.find('h1')

# Extract the number of listings from the tag text (e.g., "149 listings")
if total_listings_tag:
    total_listings = int(total_listings_tag.text.strip().split()[0])
    print("Total Listings:", total_listings)
else:
    print("Total Listings not found.")
    total_listings = 0

# Calculate the total number of pages (assuming 12 listings per page)
listings_per_page = 12
total_pages = math.ceil(total_listings / listings_per_page)
print("Total Pages:", total_pages)

# Function to dynamically find the pagination URL pattern
def get_pagination_url_pattern(soup):
    pagination_link = soup.find('a', {'aria-label': 'Next'})
    if pagination_link and 'href' in pagination_link.attrs:
        next_page_url = pagination_link['href']
        print(f"Detected Pagination URL Pattern: {next_page_url}")
        return next_page_url.replace('paginate=2', 'paginate={}')
    else:
        return None

pagination_url_pattern = get_pagination_url_pattern(soup)
if not pagination_url_pattern:
    pagination_url_pattern = base_url + '?paginate={}'

# Function to scrape property URLs from a single page
def scrape_property_urls(page_num):
    url = pagination_url_pattern.format(page_num)
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')
    
    property_urls = []
    listings = soup.find_all('div', class_='listingimage')
    
    for listing in listings:
        link = listing.find('a')
        if link and 'href' in link.attrs:
            property_url = link['href']
            full_url = f"https://www.remax.sr{property_url}"
            property_urls.append(full_url)
    
    return property_urls

# Function to scrape data from each property URL
def scrape_property_data(property_url):
    response = requests.get(property_url)
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # Extracting required data
    name = soup.find('h2').text.strip() if soup.find('h2') else None
    price = soup.find('p', class_='price').text.strip() if soup.find('p', class_='price') else None
    
    characteristics = {}
    property_table = soup.find('div', id='propertytable')

    if property_table:
        rows = property_table.find_all('tr')
        for row in rows:
            cells = row.find_all('td')
            # Iterate through pairs of adjacent cells
            for i in range(0, len(cells), 2):
                if i + 1 < len(cells):  # Ensure there is a value cell
                    key = cells[i].text.replace(":", "").strip()
                    value = cells[i + 1].text.strip()
                    if key and value:  # Add only if both key and value exist
                        characteristics[key] = value

    address = characteristics.get('Neighbourhood','')
    if address == '':
        address = characteristics.get("District","")
    area = characteristics.get("Living space", None)
    description = ''
    paragraphs = soup.find_all('p')

    # Check if there are at least two <p> elements
    if len(paragraphs) > 1:
        description = paragraphs[2].text.strip()
    else:
        description = 'Description not found'
    
    # Extract property type from breadcrumb
    breadcrumb = soup.find('ul', class_='breadcrumb')
    property_type = breadcrumb.find_all('li')[1].text.strip() if breadcrumb else None
    
    # Assuming transaction type is "sale" if found in the breadcrumb
    transaction_type = "sale" if "sale" in breadcrumb.find_all('li')[1].text.lower() else None
    
    # Extract latitude and longitude from the script
    script_tag = soup.find('script', text=lambda t: t and 'google.maps.event.addDomListener' in t)
    if script_tag:
        lat_lng_text = script_tag.string.split('new google.maps.LatLng(')[1].split(')')[0]
        latitude, longitude = lat_lng_text.split(', ')
    else:
        latitude, longitude = None, None
    
    return {
        'URL' :property_url,
        "Name": name,
        "Price": price,
        "Address": address,
        "Characteristics": characteristics,
        "Area": area,
        "Description": description,
        "Property Type": property_type,
        "Transaction Type": transaction_type,
        "Latitude": latitude,
        "Longitude": longitude
    }

# Scrape all pages and collect property URLs
all_property_urls = []
for page in range(1, total_pages + 1):
    print(f"Scraping page {page}/{total_pages}...")
    property_urls = scrape_property_urls(page)
    all_property_urls.extend(property_urls)

# Collect all property data
all_properties_data = []
for property_url in all_property_urls:
    print(f"Scraping data from {property_url}...")
    property_data = scrape_property_data(property_url)
    print(property_data)
    all_properties_data.append(property_data)

# Save the data into an Excel file
df = pd.DataFrame(all_properties_data)

# Generate Excel filename based on the base URL
excel_filename = base_url.replace('https://', '').replace('/', '_') + '.xlsx'
df.to_excel(excel_filename, index=False)

print(f"Data saved to {excel_filename}")
