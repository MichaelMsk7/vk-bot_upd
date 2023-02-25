import os

from .sql_api import PostgresAPI
import json

with open('sql_part/sql_config.json', 'r') as f:
    db_configs = json.load(f)

db_api = PostgresAPI(db_configs)
