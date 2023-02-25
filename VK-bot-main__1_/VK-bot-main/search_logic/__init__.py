from .search_module import VKSearchBot, json

with open('search_logic/bot_configs.json', 'r') as f:
    bot_configs = json.load(f)
bot = VKSearchBot(**bot_configs)
