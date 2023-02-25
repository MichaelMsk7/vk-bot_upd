import sqlalchemy
from sqlalchemy.orm import sessionmaker
from sqlalchemy_utils import database_exists, create_database, drop_database
from .models import *


class DBClient:
    def __init__(self, db_host, db_port, db_name,
                 user='postgres', password='123qweasd'):
        """Данный класс предназначен для установления подключения к базе
        данных PostgreSQL с использованием библиотеки sqlalchemy."""
        self.host = db_host
        self.port = db_port
        self.db_name = db_name
        self.user = user
        self.password = password
        self.url = 'postgresql://{}:{}@{}:{}/{}'.format(self.user,
                                                        self.password,
                                                        self.host,
                                                        self.port,
                                                        self.db_name)
        self.connection = self.connect()

        session = sessionmaker(bind=self.connection.engine,
                               autocommit=True,
                               autoflush=True,
                               enable_baked_queries=False,
                               expire_on_commit=True)
        self.session = session()
        self.engine = None

    def create_tables(self):
        """Данный метод создаёт таблицы в базе данных, которые
        подгружаются из models.py."""
        Base.metadata.create_all(self.engine)

    def get_connection(self):
        """Данный метод предназначен для получения подключения к базе
        данных."""
        try:
            self.engine = sqlalchemy.create_engine(self.url, encoding='utf8')
            return self.engine.connect()
        except:
            print('Нет доступа к базе данных приложения!')

    def connect(self):
        """Проверяет наличие нужной базы данных и в случае её отсутствия -
        создаёт пустую."""
        if database_exists(self.url):
            return self.get_connection()
        else:
            create_database(self.url)
        return self.get_connection()

    def rebuild_database(self):
        """Очищает базу данных и создаёт пустую с тем же названием."""
        if database_exists(self.url):
            drop_database(self.url)
        create_database(self.url)
        self.get_connection()
