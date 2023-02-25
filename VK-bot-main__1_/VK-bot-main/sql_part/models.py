from sqlalchemy import Column, Integer, VARCHAR, ARRAY
from sqlalchemy.ext.declarative import declarative_base
from marshmallow import Schema


Base = declarative_base()


class Users(Base):
    __tablename__ = "users"
    vk_id = Column(Integer, primary_key=True, nullable=False)
    first_name = Column(VARCHAR, nullable=False)
    last_name = Column(VARCHAR, nullable=False)
    age = Column(Integer)
    sex = Column(Integer)
    city = Column(VARCHAR(30))
    seen_users = Column(ARRAY(VARCHAR))
    found_users = Column(ARRAY(VARCHAR))


class UsersSchema(Schema):
    class Meta:
        fields = ('first_name', 'last_name', 'age', 'sex', 'city',
                  'seen_users', 'found_users')


class SearchParams(Base):
    __tablename__ = 'search_params'
    vk_id = Column(Integer, primary_key=True)
    lower_age_limit = Column(Integer)
    higher_age_limit = Column(Integer)
    sex = Column(Integer)
    city = Column(VARCHAR(30))
    marital_status = Column(VARCHAR(30))


class SearchParamsSchema(Schema):
    class Meta:
        fields = ('lower_age_limit', 'higher_age_limit',
                  'sex', 'city', 'marital_status')



