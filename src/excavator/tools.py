# Standard Library Imports
from time import sleep
from random import uniform
import requests as req
import os

# Global Imports
from bs4 import BeautifulSoup

# Local Imports

def wait():
    # Wait a random amount of time to be polite to the server and be all... sneaky about it
    wait_time = uniform(2, 4)
    sleep(wait_time)


def get_soup(
        url: str
) -> BeautifulSoup:
    page = req.get(url)
    soup = BeautifulSoup(page.content, features="lxml")
    return soup

def pull_pages(first_url):
    pages = [first_url]
    wait()
    page_soup = get_soup(first_url)
    bites = page_soup.find_all('a', {'class': 'page-numbers'})
    pages = pages + [x.get('href') for x in bites]
    return pages

def clean_string(string):
    string = string.replace('\n', '')
    while '  ' in string:
        string = string.replace('  ', ' ')
    string = string.replace(' .', '.')
    string = string.strip().strip(',')
    return string


def url_cleaner(url):
    if "https://foursouls.com" not in url:
        url = "https://foursouls.com" + url
    return url


inplace_renamer = {
    'ATK': 'STR',
    'DC': 'AC',
    'Coin': 'Cent'
}


# Wait a random amount of time to be polite to the server and be all... sneaky about it
def wait():
    wait_time = uniform(2, 4)
    sleep(wait_time)


def get_soup(url):
    page = req.get(url)
    soup = BeautifulSoup(page.content, features="lxml")
    return soup


def url_cleaner(url):
    if "https://foursouls.com" not in url:
        url = "https://foursouls.com" + url
    return url


def pull_pages(first_url):
    pages = [first_url]
    wait()
    page_soup = get_soup(first_url)
    bites = page_soup.find_all('a', {'class': 'page-numbers'})
    pages = pages + [x.get('href') for x in bites]
    return pages


def pull_card_urls(soup):
    wait()
    bites = soup.find_all('div', {'class': 'cardGridCell'})
    cards = [x.find('a').get('href') for x in bites]
    return cards


def clean_string(string):
    string = string.replace('\n', '')
    while '  ' in string:
        string = string.replace('  ', ' ')
    string = string.replace(' .', '.')
    string = string.strip().strip(',')
    return string


def translate_images(soup, icon_type='inlineIcon'):
    inline_image_dict = {x.prettify(): inplace_renamer.get(x.get('alt'), x.get(
        'alt')) for x in soup.find_all('img', {'class': icon_type})}
    for html, string in inline_image_dict.items():
        soup_string = soup.prettify().replace(html, string)
    soup = BeautifulSoup(soup_string, features="lxml")
    return clean_string(soup.text)


def grab_text(text_element, icon_type='inlineIcon'):
    text = ""
    inline_images = text_element.find_all('img', {'class': icon_type})
    if inline_images:
        text = translate_images(text_element, icon_type=icon_type)
    else:
        text = clean_string(text_element.text)
    return text


def grab_name(soup):
    name = soup.find('h1').text
    return name


def ingest_table(table_soup, icon_type='inlineIcon'):
    rows = [grab_text(x, icon_type=icon_type)
            for x in table_soup.find_all('tr')]
    return rows
