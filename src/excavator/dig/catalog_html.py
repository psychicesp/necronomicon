# Standard Library Imports
import os
import requests as req
# Global Imports

# Local Imports
from ..urls import type_urls
from ..tools import (
    pull_pages,
    wait,
    get_soup,
    pull_card_urls
)

# ----------------------------------------
# Supporting Functions
# ---------------------------------------

# ----------------------------------------
# Main Function
# ----------------------------------------

def main(config):
    """
    Blurb:

    Args:

    Returns:
    """
    html_catalog = config['html_catalog']
    for card_type, url in type_urls.items():
        folder = os.path.join(html_catalog, card_type)
        if card_type not in os.listdir(html_catalog):
            os.mkdir(folder)
        print(f'-----Getting all of the {card_type.title()}s-----')
        page_list = pull_pages(url)
        card_urls = []
        for page in page_list:
            wait()
            page_soup = get_soup(page)
            card_urls = card_urls + pull_card_urls(page_soup)
        if card_type == 'monster':
            card_urls = card_urls + \
                ["https://foursouls.com/cards/r-the_harbingers/"]
        for card_url in card_urls:
            unique_name = card_url.strip('/').split('/')[-1].replace('-', '_')
            file_name = os.path.join(folder, f"{unique_name}.html")
            if file_name not in os.listdir(folder):
                print(f'    -Grabbing {unique_name}')
                card = req.get(card_url).text
                with open(file_name, 'w', encoding="utf8") as file:
                    file.write(card)
                print(f'Grabbed {unique_name}')
            else:
                print(f'Already had {unique_name}')