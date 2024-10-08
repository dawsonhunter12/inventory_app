# config.py

import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'Jettson1245!'
    SQLALCHEMY_DATABASE_URI = 'sqlite:///inventory.db'  # Ensure this line points to your database
    SQLALCHEMY_TRACK_MODIFICATIONS = False
