# %%
# Standard Library Imports
from time import sleep
from random import uniform
import requests as req
import os

# Global Imports
from bs4 import BeautifulSoup

# Local Imports
from ..urls import type_urls, card_backs, cards_url
from ..tools import (
    ingest_table,
    grab_text,
    wait,
    clean_string,
    url_cleaner,
    get_soup,
    grab_name,
    pull_pages,
    pull_card_urls
)

# ----------------------------------------
# Supporting Functions
# ----------------------------------------


def _grab_effect_list(soup):
    effect_list = []
    effect_table = soup.find('table', {'id': 'EffectTable'})
    if effect_table:
        effect_list = ingest_table(
            effect_table, icon_type="effectModifierIcon")
    effects = soup.find_all('div', {'class': 'effectOutcome'})
    for effect in effects:
        effect_text = grab_text(effect)
        symbol = effect.find('img', {'class': 'effectIcon'})
        if symbol:
            symbol = symbol.get('alt').replace(
                ' Effect', '').replace('Paid', 'Pay')
            effect_text = symbol + ': ' + effect_text
        effect_list.append(effect_text)
    footnotes = soup.find_all('div', {'class': 'footnote'})
    if len(footnotes) > 0:
        for footnote in footnotes:
            effect_text = grab_text(footnote)
            if effect_text[0] == '-':
                footnote_tag = effect_text.strip('-').split('-')[0]
                if len(footnote_tag) > 0:
                    effect_list.append(f'-{footnote_tag}-')
                effect_text = effect_text.replace(f"-{footnote_tag}-", "")
                effect_list.append(effect_text)

    effect_list = [x for x in effect_list if len(x) > 0]
    return effect_list


def _grab_flavortext(soup):
    flavortext = soup.find('p', {'class': 'quoteText'})
    return flavortext


def _grab_starting_item(soup):
    related_card = soup.find('div', {'class': 'relatedCard'})
    card_link = related_card.find('a').get('href')
    unique_name = card_link.strip('/').split('/')[-1].replace('-', '_')
    return unique_name


def _download_image(url, loc):
    wait()
    img_data = req.get(url).content
    with open(loc, 'wb') as handler:
        handler.write(img_data)


def _grab_stats(stat_table):
    stats = {}
    rows = ingest_table(stat_table, 'statIcon')
    for row in rows:
        row_text = [clean_string(x) for x in row.split(' : ')]
        stats[row_text[0]] = row_text[1]
    return stats


def _grab_images(soup, unique_name, config, how):
    large_folder = config['large_images']
    small_folder = config['small_images']
    large_url = soup.find('a', {'rel': 'lightbox'}).get("href")
    small_url = soup.find("img").get("data-src")
    file_name = f"{unique_name}.png"
    large_loc = os.path.join(large_folder, file_name)
    small_loc = os.path.join(small_folder, file_name)
    if how == 'regular':
        _download_image(large_url, large_loc)
        _download_image(small_url, small_loc)
    # Getting card back
    card_right = soup.find('div', {'id': 'CardRight'})
    large_back_url = url_cleaner(card_right.find(
        'a', {'rel': 'lightbox'}).get("href"))
    small_back_url = url_cleaner(card_right.find("img").get("data-src"))
    if large_back_url in card_backs:
        back_name = card_backs[large_back_url]
    else:
        back_name = large_back_url.strip('/').split('/')[-1].replace('-', '_')
    if how == 'regular':
        if back_name not in os.listdir(large_folder):
            _download_image(large_back_url, os.path.join(
                large_folder, back_name))
        if back_name not in os.listdir(small_folder):
            _download_image(small_back_url, os.path.join(
                small_folder, back_name))
    image_dict = {
        'front': file_name,
        'back': back_name
    }

    return image_dict

# ----------------------------------------
# Main Functions
# ----------------------------------------

def grab_card(source, config, card_type='debug', how='regular'):
    if how == 'refresh':
        unique_name = source.split('.')[0]
        with open(os.path.join(config['html_catalog'], card_type, f"{unique_name}.html"), 'r', encoding='utf8') as file:
            html = file.read()
            soup = BeautifulSoup(html, features="lxml")
    else:
        unique_name = source.strip('/').split('/')[-1].replace('-', '_')
        soup = get_soup(source)
    card = {}
    card["type"] = card_type
    card["unique_name"] = unique_name
    card_page = soup.find('main', {'class': 'cardpage'})
    card['name'] = grab_name(card_page)
    card["image"] = _grab_images(card_page, unique_name, config, how)
    stat_table = soup.find('table', {'id': 'StatTable'})
    if stat_table:
        card['stats'] = _grab_stats(stat_table)
    if soup.find('table', {'id': 'EffectTable'}) or soup.find('div', {'class': 'effectOutcome'}):
        card['effects'] = _grab_effect_list(card_page)
    char_box = soup.find('div', {'id': 'CharitemBox'})
    if char_box:
        if char_box.find('h3').text == 'Eternal Card':
            card['starting_item'] = _grab_starting_item(char_box)
        elif char_box.find('h3').text == 'Character Card':
            card['belongs_to'] = _grab_starting_item(char_box)
    reward_table = card_page.find('table', {'id': 'RewardTable'})
    if reward_table:
        card['rewards'] = ingest_table(reward_table, 'rewardIcon')
    flavortext = soup.find('p', {'class': 'quoteText'})
    if flavortext:
        card['flavortext'] = grab_text(flavortext)
    return card


def main(
    config: dict,
    how='partial'
):
    """
    Gets all of the cards and saves their info into the DB detailed in config

    Args:
        config: a dictionary containing all of the necesssary config values, as created by archivist.check_values

        how: 
            'partial': will only grab info on unique found names
            'full': overwrites everything with newly found information
    """
    collection = config['db']['cards']
    for card_type, url in type_urls.items():
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
            already_in = collection.find_one({'unique_name': unique_name})
            if already_in:
                if how == 'full':
                    print(f'    Updating {unique_name}')
                    card = grab_card(card_url, config, card_type=card_type)
                    collection.update_one(
                        {'unique_name': card['unique_name']}, {'$set': card})
                    print(f'Updated {unique_name}')
                else:
                    print(f'Already had {unique_name}')
            else:
                print(f'    -Grabbing {unique_name}')
                card = grab_card(card_url, config, card_type=card_type)
                collection.insert_one(card)
                print(f'Grabbed {unique_name}')
