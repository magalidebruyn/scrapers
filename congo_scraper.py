"""
Web scraper for downloading laws as files from
http://www.leganet.cd/JO.htm
- the national law repository of the Democratic Republic of the Congo (DRC) -
using a Selenium Chrome bot.

Author: Magali de Bruyn
Updated: December 13, 2021
"""

## Install libraries through console
## ! pip install selenium
## ! pip install pdfkit
### ! brew install homebrew/cask/wkhtmltopdf

## Or create a virtual environment:
## pipenv install selenium
## pipenv install pdfkit
## pipenv install wkhtmltopdf / brew install wkhtmltopdf # ! this doesn't work for me
## pipenv run python scraper_tutorial.py

# This code uses a web driver
# Download from https://chromedriver.chromium.org/downloads
# based on Chrome version (version 96.0 for my local machine)

from datetime import date
import json
import os
from os import path
import re
import requests
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from bs4 import BeautifulSoup


# Define class constants
START_URL = 'http://www.leganet.cd/JO.htm' # 'http://www.ejustice.just.fgov.be/loi/loi.htm'
DOWNLOAD_PATH = './data/DRC/'
METADATA = []
METADATA_PATH = './data/DRC/metadata.json'
COUNTRY = 'DRC'

# Create fake user agent to bypass anti-robot walls
FAKE_USER_AGENT = 'Mozilla/5.0 (Windows NT 4.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/37.0.2049.0 Safari/537.36'

### GENERALIZABLE CODE
### Can be reused for other countries' websites

class ChromeBot:
    def __init__(self, headless=False):
        options = Options()
        options.headless = headless
        options.add_argument(f'user-agent={FAKE_USER_AGENT}')
        s = Service("./chromedriver")
        self.driver = webdriver.Chrome(service=s, options=options)
        print('Chrome bot initialized!')

    def navigate_to(self, url):
        try:
            self.driver.get(url)
            print(f'\nLoaded page: {url}')
        except:
            print(f'\nCould not access this page: {url}')

    def find_xpath(self, xpath):
        try:
            return self.driver.find_elements(By.XPATH, xpath)
        except IndexError:
            print('FAILED: Chrome bot could not find specified xpath.')

    def find_xpath_solo(self, xpath):
        try:
            return self.driver.find_element(By.XPATH, xpath)
        except IndexError:
            print('FAILED: Chrome bot could not find specified xpath.')

    def get_html(self):
        return self.driver.page_source

    def get_url(self):
        return self.driver.current_url

    def switch_to_default(self):
        self.driver.switch_to.default_content()

    def switch_to_frame(self, frame_xpath: str):
        frame = self.driver.find_element(By.XPATH, frame_xpath)
        self.driver.switch_to.frame(frame)

    def wait_sec(self, time_sec):
        self.driver.implicitly_wait(time_sec)

def create_destination_file(law_name: str, law_text: str, type: str, language: str = 'french'):
    """
    Define a name and file path for any law based on title, content, and desired file type
    """
    # Shorten and format the title and sample text
    title = re.sub(' ', '-', re.sub('\W+',' ', law_name)).lower()[:200]
    print(title)
    law_text = re.sub(' ', '-', re.sub('\W+',' ', law_text)).lower()[:50]
    # Create the path by combining relevant variables
    file_path = DOWNLOAD_PATH + language + '/' + type + '/' + title + law_text + '.' + type
    destination_file = os.path.join( os.path.dirname(__file__), file_path)
    # Check that the file does not already exist
    if path.exists(destination_file):
        print(destination_file + " is already downloaded. Not re-downloading.")
        return
    return destination_file

def append_to_metadata(law_name: str, file_link: str, filename: str, language: str = 'french'):
    """Append a new entry to the METADATA list."""
    METADATA.append({'title': law_name,
                     'link': file_link,
                     'download_path': filename,
                     'download_date': date.today().strftime('%Y-%m-%d'),
                     'language': language,
                     'country': COUNTRY})
    print('Added item to METADATA.')

def write_metadata_json():
    """Write the metadata to a json file."""
    dirname = os.path.dirname(__file__)
    metadata_path = os.path.join(dirname, METADATA_PATH)
    with open(metadata_path, 'w') as file:
        json.dump(METADATA, file)
    print('\nWrote metadata to JSON.')


### COUNTRY-SPECIFIC CODE
### For DRC (Congo): from www.leganet.cd/JO.htm

def scrape_drc_laws(headless=True):
    """Scrape all DRC laws from http://www.leganet.cd/JO.htm"""

    # Define language
    language = 'french'
    # Initialize Selenium Chrome bot
    bot = ChromeBot(headless)
    # Navigate to start url
    bot.navigate_to(START_URL)
    # Access laws listing page
    # Access XPath
    laws_list_link = bot.find_xpath_solo("//img[@alt='Législation']")
    # Stop if a problem occured
    if laws_list_link is None:
        return
        # Click on button
    laws_list_link.click()

    # Keep track of total laws and listing pages
    all_links = bot.find_xpath("//a[@target='_blank']")
    laws_ttl = len(all_links)

    # Iterate over all download links; click on it, scrape the law, come back to previous page
    for i in range(len(all_links)): # For testing purposes, use: range(0, 1):
        try:
            # Click on law, access page
            all_links[i].click()
            # Announce law
            print(f'Found law ({i+1}/{len(all_links)})')
            ### ! BUG HERE
            ### ! TODO: Seems to be loading the same page url & text content
            #### even though its clearly another page and web element
            #### Investigate why this is going on (is the same webpage being accessed or are we actually going to different web pages?)
            #### Figure out how to get the right info
            # Get url of page
            # ! TODO: This seems to be getting the overall url and not of specific page
            file_source_url = bot.get_url()
            # Get html text
            text_html = bot.get_html()
            # Use Beautiful Soup to get Unicode string
            soup = BeautifulSoup(text_html, features="html.parser")
            text_soup = soup.get_text()
            # Get first words of law
            law_title = text_soup[300:550] # 300:550
            # Get what it's about
            content_extract = text_soup[-300:-250]
            # Create file
            destination_file = create_destination_file(law_title, content_extract, 'txt', language)
            if destination_file is not None:
                # Write text file
                with open(destination_file, 'w') as file:
                    file.write(text_soup)
                # Add entry metadata for this law
                append_to_metadata(law_title, file_source_url, destination_file, language)
        except:
            print('Link to law does not work.')
            # !TODO: Get snippet shown on main page when link doesn't work

    # Write all metadata to JSON
    write_metadata_json()
    print(f'{laws_ttl} laws discovered in total')
    print('\nCode finished running!\n')

if __name__ == '__main__':
    scrape_drc_laws(headless=True)
