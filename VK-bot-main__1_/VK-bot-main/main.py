from search_logic import bot
from sql_part import db_api


db_api.client.create_tables()
bot.start_listening()
