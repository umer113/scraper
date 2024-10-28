import requests
from bs4 import BeautifulSoup
import json
import pandas as pd
import os

def scrape_listings(urls):
    # Define the artifacts folder for saving Excel files
    save_folder = "artifacts"

    # Create the artifacts directory if it doesn't exist
    if not os.path.exists(save_folder):
        os.makedirs(save_folder)
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'
    }
    
    for base_url in urls:
        page_number = 1
        all_listings = []

        while True:
            print("========================================================================================================================================")
            print("Scraping page number:", page_number)
            # Construct the URL for the current page
            if '?' in base_url:
                url = f"{base_url}&page={page_number}"
            else:
                url = f"{base_url}?page={page_number}"
            
            print(url)
            
            # Send a GET request to the webpage
            response = requests.get(url, headers=headers)
            
            # Check if the request was successful
            if response.status_code == 200:
                print("Successfully fetched the page.")
                # Parse the webpage content
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Find the script tag with id "__NEXT_DATA__"
                script_tag = soup.find("script", id="__NEXT_DATA__")
                
                if script_tag:
                    print("Found the script tag.")
                    try:
                        # Load the JSON data from the script tag
                        data = json.loads(script_tag.string)
                        listings_data = data['props']['pageProps']['searchResult']['listings']
                        
                        if not listings_data:
                            print("No data found in JSON. Stopping scrape for this URL.")
                            break  # Stop scraping for this URL if the data is empty
                        
                        # Extract the required data for each listing
                        for listing in listings_data:
                            property_data = listing.get('property', {})
                            location_data = property_data.get('location', {})
                            coordinates = location_data.get('coordinates', {})
                            
                            name = property_data.get('title', '')
                            price_value = property_data.get('price', {}).get('value', '-')
                            currency = property_data.get('price', {}).get('currency', '')
                            period = property_data.get('price', {}).get('period', '')
                            price = f"{price_value} {currency}/{period}" if price_value != '-' else '-'             
                            address = location_data.get('full_name', '')
                            description = property_data.get('description', '-')
                            property_type = property_data.get('property_type', '-')
                            transaction_type = property_data.get('offering_type', '-')
                            area = property_data.get('size', {}).get('value', '-')
                            amenities = ', '.join(property_data.get('amenity_names', []))
                            latitude = coordinates.get('lat', '')
                            longitude = coordinates.get('lon', '')
                            characteristics = {
                                'Property Type': property_type,
                                'Property Size': f"{area} square meters" if area else '-',
                                'Bedrooms': property_data.get('bedrooms', '-'),
                                'Bathrooms': property_data.get('bathrooms', '-'),
                                'Available From': property_data.get('listed_date', '-'),
                            }
                            property_url = 'https://www.propertyfinder.bh' + property_data.get('details_path', '-')

                            listing_data = {
                                'Name': name,
                                'Price': price,
                                'Address': address,
                                'Description': description,
                                'Property Type': property_type,
                                'Transaction Type': transaction_type,
                                'Area': str(area) + " square meters",
                                'Amenities': amenities,
                                'Characteristics': characteristics,
                                'Latitude': latitude,
                                'Longitude': longitude,
                                'Property URL': property_url
                            }
                            print("listing:",listing_data)
                            all_listings.append(listing_data)
                        
                        # Increment the page number to move to the next page
                        page_number += 1
                    except json.JSONDecodeError as e:
                        print("Error parsing JSON:", e)
                        break  # Stop scraping if there is a JSON parsing error
                else:
                    # No script tag found, assuming this is the last page
                    print(f"No script tag found on page {page_number}. Ending scrape for {base_url}.")
                    break
            else:
                print(f'Failed to retrieve the webpage. Status code: {response.status_code}')
                break
        
        # Save the data to an Excel sheet named after the base URL in the artifacts folder
        if all_listings:
            df = pd.DataFrame(all_listings)
            file_name = os.path.join(save_folder, f"{base_url.replace('https://', '').replace('/', '_').replace('?', '_').replace('&', '_').replace('=', '_')}.xlsx")
            df.to_excel(file_name, index=False)
            print(f"Data saved to {file_name}")

# List of URLs of the webpages to scrape
urls = [
    "https://www.propertyfinder.bh/en/rent/properties-for-rent.html"
    # Add your URLs here
]

# Start scraping
scrape_listings(urls)
