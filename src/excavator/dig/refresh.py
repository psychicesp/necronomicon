# Standard Library Imports
import os
# Global Imports

# Local Imports
from .cards import grab_card


def main(config):
    """
    Blurb:

    Args:

    Returns:
    """
    collection = config['db']['cards']
    folder = config['html_catalog']
    for card_type in os.listdir(folder):
        folder = os.path.join(config['html_catalog'], card_type)
        for html_file_loc in os.listdir(folder):
            card = grab_card(str(html_file_loc), config,
                             card_type=card_type, how='refresh')
            collection.replace_one(
                {'unique_name': card['unique_name']}, card, upsert=True)
            print(f'Grabbed {card["unique_name"]}')

