"""
Web scraper for downloading Belgian laws as PDFs from
http://www.ejustice.just.fgov.be/cgi/summary.pl
using a Selenium Chrome bot.

Author: Magali de Bruyn
Updated: December 10, 2021

Fun fact: this website from the Belgian government seems to have been created in 2002...
and doesn't look like it's been revamped since then -
it shows both in its design and code!
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
START_URL = 'http://www.ejustice.just.fgov.be/cgi/welcome.pl' # 'http://www.ejustice.just.fgov.be/loi/loi.htm'
BASE_URL = 'http://www.ejustice.just.fgov.be/'
DOWNLOAD_PATH = './data/belgium/'
METADATA = []
METADATA_PATH = './data/belgium/metadata.json'
COUNTRY = 'Belgium'
LANGUAGES = {'french': 'Français', 'dutch': 'Nederlands', 'german': 'Deutsch'}


# Create fake user agent to bypass anti-robot walls
FAKE_USER_AGENT = 'Mozilla/5.0 (Windows NT 4.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/37.0.2049.0 Safari/537.36'

### GENERALIZABLE CODE
### Can be reused for other countries' websites

class ChromeBot:
    def __init__(self, headless=False):
        options = Options()
        options.headless = headless
        options.add_argument(f'user-agent={FAKE_USER_AGENT}')

        # Add custom profile to disactivate PDF viewer
        profile = {
            "plugins.plugins_list": [{"enabled": False,
                                         "name": "Chrome PDF Viewer"}],
        }
        options.add_experimental_option("prefs", profile)
        s = Service("./chromedriver")
        self.driver = webdriver.Chrome(service=s, options=options)
        print('Chrome bot initialized!')

    def navigate_to(self, url):
        try:
            self.driver.get(url)
            print(f'Loaded page: {url}')
        except:
            print(f'Could not access this page: {url}')

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

    def switch_to_default(self):
        self.driver.switch_to.default_content()

    def switch_to_frame(self, frame):
        self.driver.switch_to.frame(frame)

    def wait_sec(self, time_sec):
        self.driver.implicitly_wait(time_sec)


def filename_maker(law_name: str) -> str:
    """Returns a lowercase, 250 characters max version of law_name
    to be used as filename (also, removes special characters)."""
    return re.sub(' ', '-', re.sub('\W+',' ', law_name)).lower()[:250]

def generate_file_name(law_name: str, type: str, language: str) -> str:
    title = filename_maker(law_name)
    return DOWNLOAD_PATH + language + '/' + type + '/' + title + '.' + type

def create_destination_file(title: str, type: str, language: str):
    html_destination_file = os.path.join(
        os.path.dirname(__file__),
        generate_file_name(title, type, language)
    )
    if path.exists(html_destination_file):
        print(html_destination_file + " already downloaded")
        return
    return html_destination_file

def append_to_metadata(law_name: str, pdf_link: str, filename: str, language: str):
    """Appends an item to the METADATA list."""
    METADATA.append({'title': law_name,
                     'link': pdf_link,
                     'download_path': filename,
                     'download_date': date.today().strftime('%Y-%m-%d'),
                     'language': language,
                     'country': COUNTRY,})
    print('Added item to METADATA.')

def write_metadata_json():
    """Writes the metadata to a json file."""
    dirname = os.path.dirname(__file__)
    metadata_path = os.path.join(dirname, METADATA_PATH)
    with open(metadata_path, 'w') as file:
        json.dump(METADATA, file)
    print('\nWrote metadata to JSON.')


### COUNTRY-SPECIFIC CODE
### For Belgium: from www.ejustice.just.fgov.be

def scrape_belgium_laws(headless=True):
    """Scrapes all Belgian laws from www.ejustice.just.fgov.be"""

    # Initialize Selenium Chrome bot and navigate to start url
    bot = ChromeBot(headless)
    bot.navigate_to(START_URL)
    bot.wait_sec(5)

    # Each law page (and corresponding file) has the same source url
    # i.e. each law page is only accessible via navigation from the start url
    # not directly
    file_source_url = 'www.ejustice.just.fgov.be/cgi/article.pl'

    for language in list(languages):
        # Access language button & corresponding laws listing page
        # Access XPath
        laws_list_link = bot.find_xpath_solo("//input[@type='Submit' and @value='{}']".format(LANGUAGES.get(language))) # dynamic XPath
        # Stop if a problem occured
        if laws_list_link is None:
            return
        # Click on button
        laws_list_link.click()

        # Access & collect link to each law on the page
        # Switch to frame
        frame1 = bot.find_xpath_solo("/html/frameset/frame[2]")
        bot.switch_to_frame(frame1)
        all_links = bot.find_xpath("//input[@type='submit' and @name='numac']")

        print(f'Laws to download on the page: {len(all_links)}\n')

        # Iterate over all download links; click on it, scrape the law, come back to previous page
        for i in range(0, len(all_links)):
            # Click on law, access page
            all_links[i].click()
            # Switch to frame containing heading/title
            frame2 = bot.find_xpath_solo("/html/frameset/frame[2]")
            bot.switch_to_frame(frame2)
            # Get title
            law_title = bot.find_xpath_solo("/html/body/h3/center/u").text
            print(f'\nFound law ({i+1}/{len(all_links)}): ', law_title)

            # Write text file
            # Get html text
            text_html = bot.get_html()
            # Use Beautiful Soup to get Unicode string
            soup = BeautifulSoup(text_html, features="html.parser")
            text_soup = soup.get_text()
            # Create file
            destination_file = create_destination_file(law_title, 'txt', language)
            if destination_file is not None:
                with open(destination_file, 'w') as file:
                    file.write(text_soup)
                # Add entry metadata for this law
                append_to_metadata(law_title, file_source_url, destination_file, language)

            # Exit frame and go back to listing
            bot.switch_to_default()
            frame3 = bot.find_xpath_solo("/html/frameset/frame[3]")
            bot.switch_to_frame(frame3)
            # Click button to go back to menu
            button_back = bot.find_xpath_solo("/html/body/table/tbody/tr/td[4]/form/input[5]")
            button_back.click()
            # Switch to frame
            bot.switch_to_default()
            frame1 = bot.find_xpath_solo("/html/frameset/frame[2]")
            bot.switch_to_frame(frame1)
            bot.wait_sec(1)
            # Recollect all links
            # Apparently necessary because otherwise not recognize link
            # ! TODO (during winter break): REFACTOR this loop
            # to make less computationally repetitive and expensive
            all_links = bot.find_xpath("//input[@type='submit' and @name='numac']")

        # Write all metadata to JSON
        write_metadata_json()

    print('\nCode finished running!\n')

if __name__ == '__main__':
    scrape_belgium_laws(headless=True)
