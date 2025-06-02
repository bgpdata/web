"""
BGPDATA - A BGP Data Aggregation Service.
© 2024 BGPDATA. All rights reserved.
"""
from flask import session, current_app as app
from datetime import datetime
from bson import ObjectId
from utils.database import db
import pytz
import re

def is_valid_email(email):
    return re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email)