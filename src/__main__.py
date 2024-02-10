#%%
#%%
from archivist import check_environment, index, study
from excavator.dig import cards, refresh, catalog_html
from evangelist.scripture import recite

print('Got changes')

config = check_environment()
catalog_html(config)
cards(config, how = 'full')
refresh(config)
index(config['db']['cards'])
# study(config['db'])
image_folder = config['large_images']

while True:
    recite(config['db']['cards'], image_folder)
# %%
