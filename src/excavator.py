# %% Imports
from bs4 import BeautifulSoup, Tag
import re
from copy import copy
import requests as req
from time import sleep
from pprint import pprint
from random import uniform
import os
# %% URLs

initial_url = "https://foursouls.com/card-search/?searchtext&origin&card_type&card_footnotes&competitive_only&identical=yes&cardstatus=cur&holo&printstatus&franchise&fullartist&charartist&backartist"

rules_url = "https://foursouls.com/rules/"

type_urls = {
    "character": "https://foursouls.com/card-search/?card_type=character",
    "starting_item": "https://foursouls.com/card-search/?card_type=eternal",
    "treasure": "https://foursouls.com/card-search/?card_type=treasure",
    "bonus_soul": "https://foursouls.com/card-search/?card_type=bsoul",
    "loot": "https://foursouls.com/card-search/?card_type=loot",
    "monster": "https://foursouls.com/card-search/?card_type=monster",
    "room": "https://foursouls.com/card-search/?card_type=room"
    # "outside": "https://foursouls.com/card-search/?card_type=outside",
}

card_backs = {
    "https://foursouls.com/wp-content/uploads/2021/10/EternalCardBack.png": "eternal_back.png",
    "https://foursouls.com/wp-content/uploads/2021/10/CharacterCardBack.png": "character_back.png",
    "https://foursouls.com/wp-content/uploads/2021/10/TreasureCardBack.png": "treasure_back.png",
    "https://foursouls.com/wp-content/uploads/2021/10/LootCardBack.png": "loot_back.png",
    "https://foursouls.com/wp-content/uploads/2021/10/MonsterCardBack.png": "monster_back.png",
    "https://foursouls.com/wp-content/uploads/2021/10/BonusSoulCardBack.png": "soul_back.png",
    "https://foursouls.com/wp-content/uploads/2021/10/RoomCardBack.png": "room_back.png",
}

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


# %% Basic Functions for extracting from bs4
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


def grab_effect_list(soup):
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


def grab_flavortext(soup):
    flavortext = soup.find('p', {'class': 'quoteText'})
    return flavortext


def grab_starting_item(soup):
    related_card = soup.find('div', {'class': 'relatedCard'})
    card_link = related_card.find('a').get('href')
    unique_name = card_link.strip('/').split('/')[-1].replace('-', '_')
    return unique_name


def download_image(url, loc):
    wait()
    img_data = req.get(url).content
    with open(loc, 'wb') as handler:
        handler.write(img_data)


def grab_stats(stat_table):
    stats = {}
    rows = ingest_table(stat_table, 'statIcon')
    for row in rows:
        row_text = [clean_string(x) for x in row.split(' : ')]
        stats[row_text[0]] = row_text[1]
    return stats


def grab_images(soup, unique_name, config, how):
    large_folder = config['large_images']
    small_folder = config['small_images']
    large_url = soup.find('a', {'rel': 'lightbox'}).get("href")
    small_url = soup.find("img").get("data-src")
    file_name = f"{unique_name}.png"
    large_loc = os.path.join(large_folder, file_name)
    small_loc = os.path.join(small_folder, file_name)
    if how == 'regular':
        download_image(large_url, large_loc)
        download_image(small_url, small_loc)
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
            download_image(large_back_url, os.path.join(
                large_folder, back_name))
        if back_name not in os.listdir(small_folder):
            download_image(small_back_url, os.path.join(
                small_folder, back_name))
    image_dict = {
        'front': file_name,
        'back': back_name
    }

    return image_dict


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
    card["image"] = grab_images(card_page, unique_name, config, how)
    stat_table = soup.find('table', {'id': 'StatTable'})
    if stat_table:
        card['stats'] = grab_stats(stat_table)
    if soup.find('table', {'id': 'EffectTable'}) or soup.find('div', {'class': 'effectOutcome'}):
        card['effects'] = grab_effect_list(card_page)
    char_box = soup.find('div', {'id': 'CharitemBox'})
    if char_box:
        if char_box.find('h3').text == 'Eternal Card':
            card['starting_item'] = grab_starting_item(char_box)
        elif char_box.find('h3').text == 'Character Card':
            card['belongs_to'] = grab_starting_item(char_box)
    reward_table = card_page.find('table', {'id': 'RewardTable'})
    if reward_table:
        card['rewards'] = ingest_table(reward_table, 'rewardIcon')
    flavortext = soup.find('p', {'class': 'quoteText'})
    if flavortext:
        card['flavortext'] = grab_text(flavortext)
    return card

# %%  Getting the rules

# with open('Motley_Mess_sample.html', 'r') as html:
#     menu_soup = BeautifulSoup(html.read(), 'lxml')

# the strategy for straining the soup involves adding recursion objects. This will remove them when we're done:
def kill_parents(soup_dict):
    if isinstance(soup_dict, dict):
        if '_parent_' in soup_dict:
            del soup_dict['_parent_']
        for key in soup_dict:
            kill_parents(soup_dict[key])


def get_header_levels(soup):
    headers = soup.find_all(re.compile('h[1-6]$'))
    unique_header_set = set([x.name for x in headers])
    unique_headers = sorted(list(unique_header_set), key=lambda x: int(x[1]))
    return unique_headers

# This is basically find_all, except that it gets all siblings up to the next element, rather than the only found elements
def split_soup(soup, tags):
    elements = soup.find_all(tags, recursive=False)
    print(elements)
    bites = []
    
    for element in elements:
        if next_element.find_next_sibling():
            next_element = element.find_next_sibling()
            while next_element not in elements or next_element.text.strip()[-1] == ':':
                element = element.append(next_element)
                if next_element.find_next_sibling():
                    next_element = next_element.find_next_sibling()
            bites.append(element)
    return bites

# Determine tag label, which should he header text if it is a header, otherwise tag name
def get_tag(bite):
    first_element = bite.find()
    if first_element.name in re.compile('h[1-6]$'):
        return first_element.text
    else:
        return first_element.name


def parse_element(element, tags, outline, prefix=""):
    # Need to keep track of which number in case of repeated elements
    nums = {
        'p': 1,
        'li': 1
    }
    for bite in split_soup(element, tags):
        print('bite')
        tag = get_tag(bite)
        if tag in nums:
            tag = f"{tag}{str(nums[tag])}"
            nums[tag] += 1
        key = prefix + f"-{tag}"
        value = bite
        outline[key] = value
    return outline
    
def has_subelement(soup_element, tags_of_interest = ['h1','h2','h3','h4','h5','h6'] + ['p', 'li']):
    element_children = [x for x in soup_element.find_all(tags_of_interest)]
    

# This will do the actual unpacking of elements in the outline and add them as new keys to the outline
def outline_populator(soup):
    header_levels = get_header_levels(soup)
    outline = {}
    outline = parse_element(soup, header_levels[0], outline)
    tags_of_interest = header_levels[1:]
    for tag in tags_of_interest:
        for key, value in outline.items():
            parse_element(value, tag, outline, key)
    return outline

# Not sure this is necessary with the new strategy, but I'll hang onto it for now
def get_elements_with_text(soup):
    elements = []
    for tag in soup.find_all():
        if tag.text.strip():
            elements.append(tag)
    return elements


def get_all_tags(soup):
    tags = []
    for tag in soup.find_all(True):
        tags.append(tag.name)
    return tags

# We need to check if elements are headings alot:
def is_header(element):
    return element.name and re.match("^h[1-6]$", element.name)


def divide_rules(soup):
    if isinstance(soup, str):
        soup = BeautifulSoup(soup, 'lxml')

    header_levels = get_header_levels(soup)
    for header_level in header_levels:
        pass


def conquer_rules(soup):
    pass


def to_outline(soup):
    outline = {}
# Split a beautiful soup object into a dictionary of beautiful soup oibjects based on the highest available

# While the dictionary contains nested header elements, repeat this process, adding extracted header sections to the parent dictionary
# Dictionary structure is to be kept flat and hierarchy should be inferred by chaining together header levels.
# Looping through header-levels and using split_soup() on each level should just kinda work.

# When no values contain header elements begin a similar process.  While elements contain sub-elements of interest ('ul', 'ol', 'p') extract top levels.
# As there are no titles as with headers, key names will need to be appended with something like 'p1.'
# in the case if nested this may result in endings like 'p1_li2_p1'
# Later we'll need to deal with p objects which preceed with a bolded word and a colon.  I'd like to use that word rather than f'p{i}'

# Add each key-value pair to the rules database


# v1 strainer, only one that works...kinda
# def unpack_headers(soup):
#     strainer = {}
#     headers = soup.find_all(re.compile('h[1-6]$'))

#     current_dict = strainer
#     previous_header = 0

#     for header in headers:
#         header_level = int(header.name[-1])
#         header_text = header.text

#         # If the current header is a lower level than the previous header, move back to the appropriate parent level in the dictionary
#         while header_level <= previous_header:
#             current_dict = current_dict['_parent_']
#             previous_header -= 1

#         # Add a new dictionary for the current header at the current level
#         current_dict[header_text] = {}
#         current_dict[header_text]['_parent_'] = current_dict
#         self_soup = header

#         current_dict[header_text]['_self_'] = self_soup

#         # Set the current dictionary to the new one we just created, and increase the previous header level
#         current_dict = current_dict[header_text]
#         previous_header = header_level

    # strainer = {}
    # headers = soup.find_all(re.compile('h[1-6]$'))

    # current_dict = strainer
    # previous_header = 0

    # for header in headers:
    #     header_level = int(header.name[-1])
    #     header_text = header.text

    #     # If the current header is a lower level than the previous header, move back to the appropriate parent level in the dictionary
    #     while header_level <= previous_header:
    #         current_dict = current_dict['_parent_']
    #         previous_header -= 1

    #     # Add a new dictionary for the current header at the current level
    #     current_dict[header_text] = {}
    #     current_dict[header_text]['_parent_'] = current_dict

    #     # Capture elements between this heading and next
    #     elements_between_headings = header.find_next_siblings(text=False)
    #     self_soup = copy(header)
    #     for element in elements_between_headings:
    #         if is_header(element):
    #             break
    #         else:
    #             self_soup.append(element)
    #     current_dict[header_text]['_self_'] = self_soup

    #     # Set the current dictionary to the new one we just created, and increase the previous header level
    #     current_dict = current_dict[header_text]
    #     previous_header = header_level

    # return strainer

# TODO (this doesnt work yet)
# Sort the html soup into a tiered dictionary based on header level to streamline naming later
# This gets a little weedy, hence its level of commenting
# def soup_strainer(soup):
#     if isinstance(soup, str):
#         soup =  BeautifulSoup(soup, 'html.parser')

#     # Keep track of the current header level and the current div
#     current_header_level = 0
#     current_div = soup

#     # Iterate through the tags in the HTML
#     for tag in soup.find_all():
#         if tag.name.startswith('h'):
#             # If the tag is a header, get its level
#             header_level = get_header_level(tag)

#             # If the header level is equal to or higher than the current header level,
#             # add a new div with the appropriate id to the current div
#             if header_level >= current_header_level:
#                 div = Tag(name='div')
#                 div['id'] = tag.text.replace(' ', '_') + f'-{header_level}'
#                 current_div.append(div)
#                 current_div = div

#             # Otherwise, add the header to the parent div of the current div
#             else:
#                 current_div.parent.append(tag)

#             # Update the current header level
#             current_header_level = header_level

#         else:
#             # If the tag is not a header, add it to the current div
#             current_div.append(tag)

#     return soup.prettify()

    # headings = soup.find_all(re.compile("^h[1-6]$"))

    # # to store the nested hierarchy of headings
    # strainer = {}

    # # iterate over all heading tags
    # for i, heading in enumerate(headings):
    #     # get the text of the heading
    #     heading_text = heading.text

    #     # initialize a dictionary to store the current heading and its subheadings
    #     current_strainer = {}

    #     # find all the elements between the current heading and the next heading
    #     # (or all further headings if final)
    #     elements_between_headings = heading.find_next_siblings(text=False)
    #     elements = []

    #     for element in elements_between_headings:
    #         elements_html.append(str(element))

    #         # if the current element is a heading, break the loop
    #         if element.name and re.match("^h[1-6]$", element.name):
    #             break
    #         # check if the current element is a list
    #         if element.name == "ul":
    #             # if the current element is a list, find its sublists
    #             sublists = element.find_all("ul")
    #             # if the current list has sublists, remove them from the elements_between_headings list
    #             # and append their html to the elements_html list
    #             if sublists:
    #                 for sublist in sublists:
    #                     sublists.remove(sublist)
    #                     elements_html.append(str(sublist))

    #     # _self_ key gets all elements between current heading and next heading (including current)
    #     # (as soup object)
    #     strained_section = "".join(elements_html)
    #     if soup_self:
    #         strained_section = BeautifulSoup("".join(elements_html), 'html.parser')
    #     current_strainer["_self_"] = strained_section

    #     # if the current heading is a subheading, add it to the dictionary of the parent heading
    #     # (parent heading is always the previous heading)
    #     if heading.name != "h1":
    #         parent_heading_text = headings[i - 1].text
    #         if parent_heading_text not in strainer:
    #             strainer[parent_heading_text] = {}
    #         strainer[parent_heading_text].update(current_strainer)
    #     else:
    #         # if the current heading is a main heading, add it to the top-level dictionary
    #         strainer[heading_text] = current_strainer

    # return strainer

    # if isinstance(soup, str):
    #     soup = BeautifulSoup(soup, 'html.parser')

    # headings = soup.find_all(re.compile("^h[1-6]$"))

    # # to store the nested hierarchy of headings
    # strainer = {}

    # # iterate over all heading tags
    # for i, heading in enumerate(headings):
    #     # get the text of the heading
    #     heading_text = heading.text

    #     # initialize a dictionary to store the current heading and its subheadings
    #     current_strainer = {}

    #     # find all the elements between the current heading and the next heading
    #     # (or all further headings if final)
    #     elements_between_headings = heading.find_next_siblings(text=False)

    #     # _self_ key gets all elements between current heading and next heading (including current)
    #     # (as soup object)
    #     strained_section = "".join(str(element) for element in elements_between_headings)
    #     if soup_self:
    #         strained_section = BeautifulSoup(strained_section, 'html.parser')
    #     current_strainer["_self_"] = strained_section

    #     # if the current heading is a subheading, add it to the dictionary of the parent heading
    #     # (parent heading is always the previous heading)
    #     if heading.name != "h1":
    #         parent_heading_text = headings[i - 1].text
    #         if parent_heading_text not in strainer:
    #             strainer[parent_heading_text] = {}
    #         strainer[parent_heading_text].update(current_strainer)
    #     else:
    #         # if the current heading is a main heading, add it to the top-level dictionary
    #         strainer[heading_text] = current_strainer

    # return strainer


def grab_rules(config):
    # rules = config['db']['rules']get
    rule_soup = get_soup(rules_url)
    links = rule_soup.find('main').find_all('li')
    for link in links:
        link_namepath = link.text
        cat_url = link.find('a').get('href')
        cat_soup = get_soup(cat_url)
        # Best solved by a recursive, dynamic, header interpreter


# %%
def catalog_html(config):
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

# %%


def dig(config, how='partial'):
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


def refresh(config):
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


# %%
