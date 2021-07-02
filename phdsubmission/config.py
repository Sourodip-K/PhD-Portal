import os
import psycopg2

class Config:
    SECRET_KEY = '0242ed1b0787e83ea2de44f4ceb504b7'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_DATABASE_URI = 'sqlite:///site.db'