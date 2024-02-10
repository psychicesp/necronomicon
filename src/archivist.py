#%%

from pymongo import MongoClient, TEXT
import os
import yaml
from yaml import Loader
import json

#This is the parent folder name to be used as the archive
folder_name = 'four_souls_storage'
config_name = 'cfg.yaml'

folder_delimiter = os.path.join('A', 'A').replace('A', '')

def connect(port):
    conn = MongoClient('localhost', port)
    cur = conn['four_souls']
    return cur

# Find folder
def find_folder(location = False):
    if not location:
        location = os.getcwd()
    if os.getcwd() == folder_name:
        folder = location
    elif folder_name in os.listdir(location):
        if os.path.isdir(os.path.join(location, folder_name)):
            folder = os.path.join(location, folder_name)
        else:
            folder = os.path.join(location, folder_name)
            os.remove(folder)
            os.mkdir(folder)
        return folder
    else:
        folder = os.path.join(location, folder_name)
        os.mkdir(folder)
    return folder

# Check if current folder structure is valid and collection is functional:
def check_environment(location = ''):
    folder = find_folder(location)
    images = os.path.join(folder, 'images')
    html_catalog = os.path.join(folder, 'html_catalog')
    large_images = os.path.join(images, 'large')
    small_images = os.path.join(images, 'small')
    config_loc = os.path.join(folder, config_name)

    files = os.listdir(folder)
    if 'images' in files:
        if os.path.isdir(images):
            if 'small' not in os.listdir(images):
                os.mkdir(small_images)
            if 'large' not in os.listdir(images):
                os.mkdir(large_images)
        else:
            os.remove(images)
            os.mkdir(images)
            os.mkdir(small_images)
            os.mkdir(large_images)
    else:
        os.mkdir(images)
        os.mkdir(small_images)
        os.mkdir(large_images)
    if 'html_catalog' not in files:
        os.mkdir(html_catalog)

    if os.path.exists(config_loc):
        with open(config_loc, 'r') as config_file:
            config = yaml.load(config_file.read(), Loader)
    else:
        config = {}
    if 'port' in config:
        port = config['port']
    else:
        port = 'string'
        while not port.isnumeric():
            port = input("Please enter a the valid port number for the local MongoDB service;\nor leave blank for 27017") or "27017"
        port = int(port)
        config['port'] = port
    config['small_images'] = small_images
    config['large_images'] = large_images
    config['html_catalog'] = html_catalog
    config['folder'] = folder
    with open(config_loc, 'w') as config_file:
        print(f'Writing file in {config_loc}')
        config_file.write(yaml.dump(config))
        print('Wrote file')
    config['db'] = connect(port)
    return config

def index(collection):
    collection.create_index([
        ("effects", TEXT),
    ],
    weights = {
        'name': 100,
        'tags': 100,
        'unique_name': 5,
        'effects': 150,
        'flavortext': 1,
        'starting_item': 1
    },
        default_language='english',
        background = True,
        name = 'text')

def annotate(db):
    pass

def objectify_string(string):
    string = string.replace('=', ':')
    while '::' in string:
        string = string.replace('::', ':')
    if ':' in string and '{' not in string:
        string_list = [x.strip() for x in string.split(',')]
        string = '\n'.join(string_list)
        out_obj = yaml.load(string, Loader)
        return out_obj
    elif '{' in string:
        out_obj = json.loads(string)
        return out_obj
    else:
        return False

# Search result hierarchy to be possibly implemented at some point [name > tag > unique_name search, effects_search, > starting_item search= belongs_to search > flavortext search] 

def search(string, collection, previous_result = []):
    obj = False
    if '=' in string:
        obj = objectify_string(string)
    if obj:
        search_results = list(collection.find(obj))
    elif string == '--ALL':
        search_results = list(collection.find({}))
    else:
        search_results = list(collection.find({'$text':{'$search': string}}, {'score': {'$meta': 'textScore'}}))
    if len(previous_result) > 0:
        previous_ids = [x['unique_name'] for x in previous_result]
        search_results = [x for x in search_results if x['unique_name'] in previous_ids]

    return search_results
    
def clean_search(doc_list):
    for doc in doc_list:
        if 'score' not in doc:
            doc['score'] = 'Not Scored'
    out_doc_list = []
    names = set([x['name'] for x in doc_list])
    for name in names:
        name_list = [x for x in doc_list if x['name'] == name]
        if len(name_list)>1:
            name_list = [x for x in name_list if x['unique_name'].split('_')[0] not in ['aa','ret']]
        name_list = sorted(name_list, key = lambda x: x['unique_name'].split('_')[0])
        out_doc_list.append(name_list[-1])
    return out_doc_list

def multifilter(filter_list, collection):
    result = []
    for query in filter_list:
        if isinstance(query, str):
            result = search(query, collection, result)
        elif callable(query):
            result = filter(query, result)
    return list(result)


def study(db):
    #       ---tag---
    cards = db.cards
    # Dealing with cards that bear a '-Tag-'
    curse_cards = multifilter(['type = monster', lambda x: "-Curse-" in x.get('effects', [])], cards)
    for card in curse_cards:
        cards.update_one({'unique_name': card['unique_name']}, {'$addToSet': {'tags': "curse"}})

    curse_cards = multifilter(['type: loot', lambda x: "-Ambush-" in x.get('effects', [])], cards)
    for card in curse_cards:
        cards.update_one({'unique_name': card['unique_name']}, {'$addToSet': {'tags': "ambush"}})

    curse_cards = multifilter(['--ALL', lambda x: "-Eternal-" in x.get('effects', [])], cards)
    for card in curse_cards:
        cards.update_one({'unique_name': card['unique_name']}, {'$addToSet': {'tags': "eternal"}})

    curse_cards = multifilter(['--ALL', lambda x: "-Guppy-" in x.get('effects', [])], cards)
    for card in curse_cards:
        cards.update_one({'unique_name': card['unique_name']}, {'$addToSet': {'tags': "guppy"}})

    curse_cards = multifilter(['type: monster', lambda x: "-Indomitable-" in x.get('effects', [])], cards)
    for card in curse_cards:
        cards.update_one({'unique_name': card['unique_name']}, {'$addToSet': {'tags': "indomitable"}})

    curse_cards = multifilter(['type: loot', lambda x: "-Trinket-" in x.get('effects', [])], cards)
    for card in curse_cards:
        cards.update_one({'unique_name': card['unique_name']}, {'$addToSet': {'tags': "trinket"}})
    # event cards are monster cards with no stats and no curse tag
    event_cards = multifilter(
        [
            'type = monster',
            lambda x: 'stats' not in x, 
            lambda x: 'curse' not in x.get('tags', [])
        ], 
        cards
    )
    for card in event_cards:
        cards.update_one({'unique_name': card['unique_name']}, {'$addToSet': {'tags': "event"}})

    # PVP contains "can be attacked" and AC
    ac_cards = search('"AC"', cards)
    pvp_cards = search('"can be attacked"', cards, ac_cards) + search('"may attack"', cards, ac_cards)
    for card in pvp_cards:
        cards.update_one({'unique_name': card['unique_name']}, {'$addToSet': {'tags': "pvp"}})

    # Items are eternal, treasures, or trinket
    item_cards = search('type = starting_item', cards) + search('type = treasure', cards) + multifilter(['type = loot', lambda x: 'trinket' in x.get('tags', [])], cards)
    for card in item_cards:
        cards.update_one({'unique_name': card['unique_name']}, {'$addToSet': {'tags': 'item'}})

    


# %%
#%%