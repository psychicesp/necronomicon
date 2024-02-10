#%%
import questionary
import os
from archivist import search, clean_search

def check_equal(card, collection):
    matches = collection.find({'name': card['name']})
    matches = [x for x in matches if x != card]
    unique_matches = {}
    unique_strings = [" ".join(card.get('effects', ''))]
    for match in matches:
        effect_string = " ".join(match.get('effects', ''))
        if effect_string not in unique_strings:
            unique_strings.append(effect_string)
            if len(effect_string) > 53:
                effect_string = effect_string[:50] + "..."
            elif len(effect_string) == 0:
                effect_string = match['unique_name']
            effect_string = 'Different Version: ' + effect_string
            unique_matches[effect_string] = match
    if len(unique_matches) > 0:
        return unique_matches
    else:
        return False

def display_card(card, image_folder, collection):
    stat_line = "   "
    print(f"\n{card['type']} card:\n")
    print(f"    ======= {card['name']} =======\n")
    if "stats" in card:
        for key, value in card['stats'].items():
            stat_line = stat_line + f"   [{key.upper()}]: {value}"
        stat_line = stat_line + '\n'
        print(stat_line)
    if "effects" in card:
        print('---Effects---')
        for effect in card['effects']:
            print(effect.replace('.', '.\n').strip('\n'))
        print('-----')
    if "flavortext" in card:
        print("\x1B[3m" + card['flavortext'] + "\x1B[0m")
        print('-----')
    if "rewards" in card:
        reward_text = "Potential Rewards:"
        for reward in card["rewards"]:
            reward_text = reward_text + f" {reward},"
        reward_text = reward_text.strip(',')
        print(reward_text)
    print(f"\nfront: {os.path.join(image_folder, card['image']['front'] )}\nback: {os.path.join(image_folder, card['image']['back'] )}".replace("\\", "\\\\"))
    options = []
    related_cards = {}
    possible_relationships = ['starting_item','belongs_to']
    for relation in possible_relationships:
        if relation in card:
            new_card = collection.find_one({"unique_name": card[relation]})
            option = f"View {relation.replace('_',' ').title()}: {new_card['name']}".replace('_',' ')
            options.append(option)
            related_cards[option] = new_card
    unique_matches = check_equal(card, collection)
    if unique_matches:
        options = list(unique_matches.keys()) + options
        related_cards.update(unique_matches)
    options.append('-- New Search --')
    selection = questionary.select(
                    "",
                    choices = options,
                    pointer = '>:>',
                    qmark = ""
                    ).ask()
    if selection in ['-- New Search --']:
        if selection == '-- New Search --':
            recite(collection, image_folder)
    else:
        display_card(related_cards[selection], image_folder, collection)
        


def recite(collection, image_folder, old_result = []):
    query = input('>:>')
    result_cursor = search(query, collection, old_result)
    clean_results = sorted(clean_search(result_cursor), key = lambda x: x['score'], reverse = True)
    results = {f"View: {x['name']}": x for x in clean_results[:10]}
    basic_options = ['-- New Search --', '-- Search Within --']
    options = basic_options + list(results.keys())
    selection = questionary.select(
                    f"Query generated {len(clean_results)} results\n Please select an option",
                    choices = options,
                    pointer = '>:>',
                    qmark = ""
                    ).ask()
    if selection in basic_options:
        if selection == '-- New Search --':
            recite(collection, image_folder)
        elif selection == '-- Search Within --':
            recite(collection, image_folder, old_result = clean_results)
    else:
        display_card(results[selection], image_folder, collection)


# %%
