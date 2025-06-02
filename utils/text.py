"""
BGPDATA - A BGP Data Aggregation Service.
© 2024 BGPDATA. All rights reserved.
"""
from bs4 import BeautifulSoup, Comment
from flask import current_app as app
from datetime import datetime
from utils.database import db
import hashlib
import bleach
import re
import pytz
import html

def date_text(dt, format_str) -> str:
    if dt is None:
        return ""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=pytz.utc)
    return dt.strftime(format_str)

def season_text(month, day) -> str:
    if month in [12, 1, 2]:
        if month == 12 and day >= 20:
            return "Weihnachtszeit"
        elif month == 1 and day <= 6:
            return "Weihnachtszeit"
        else:
            return "tiefster Winter"
    elif month in [3, 4, 5]:
        if month == 3 and day <= 20:
            return "Frühwinter"
        else:
            return "Frühling"
    elif month in [6, 7, 8]:
        if month == 7 or (month == 6 and day >= 21) or (month == 8 and day <= 20):
            return "Hochsommer"
        else:
            return "Sommer"
    else:  # 9, 10, 11
        if month == 9 and day >= 21:
            return "Herbst"
        elif month == 11 and day >= 20:
            return "Vorweihnachtszeit"
        else:
            return "Spätsommer"

def time_ago(dt) -> str:
    now = datetime.now(pytz.utc)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=pytz.utc)

    diff = now - dt

    seconds = diff.total_seconds()
    minutes = seconds // 60
    hours = minutes // 60
    days = hours // 24
    years = days // 365

    if seconds < 60:
        if int(seconds) == 0:
            return "ein paar Sekunden"
        return f"{int(seconds)} { 'Sekunde' if seconds == 1 else 'Sekunden' }"
    elif minutes < 60:
        return f"{int(minutes)} { 'Minute' if minutes == 1 else 'Minuten' }"
    elif hours < 24:
        return f"{int(hours)} { 'Stunde' if hours == 1 else 'Stunden' }"
    elif days < 30:
        return f"{int(days)} { 'Tag' if days == 1 else 'Tagen' }"
    elif years < 1:
        months = days // 30
        return f"{int(months)} { 'Monat' if months == 1 else 'Monate' }"
    else:
        return f"{int(years)} { 'Jahr' if years == 1 else 'Jahre' }"


def hash_text(text) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def format_text(text) -> str:
    # Normalize whitespace around newlines
    text = re.sub(r'[ \t]*\n[ \t]*', '\n', text)

    # Replace lines containing only whitespaces with a single newline
    text = re.sub(r'\n\s*\n', '\n\n', text)

    # Replace multiple newlines with a maximum of two
    text = re.sub(r'\n{2,}', '\n\n', text)

    # Convert http links to https
    text = re.sub(r'http://', 'https://', text)

    # Wrap links with <a> tags
    text = re.sub(r'(https?://\S+)', r'<a href="\1">\1</a>', text)

    # Replace single-newlines with <br/>
    text = re.sub(r'\n', '<br/>', text)

    # Reduce multiple consecutive empty newlines to a single empty newline
    text = re.sub(r'\n\s*\n', '\n\n', text)

    return text

def url_alias(id, title):
    # Clean the title
    clean_title = clean_text(title)
    
    # Replace spaces with hyphens
    hyphenated = clean_title.replace(' ', '-')
    
    # Convert to lowercase
    lowered = hyphenated.lower()
    
    # Convert umlauts to regular characters
    no_umlauts = lowered.translate(str.maketrans({
        'ä': 'ae',
        'ö': 'oe', 
        'ü': 'ue',
        'ß': 'ss'
    }))
    
    # Keep only alphanumeric and hyphen characters
    alphanumeric = ''.join(c for c in no_umlauts if c.isalnum() or c == '-')
    
    return f"{str(id)}-{alphanumeric}"

def clean_text(text) -> str:
    if text:
        return bleach.clean(text)
    else:
        return "" 
    
def sanitize_text(text):
    ALLOWED_TAGS = {
        'b', 'strong', 'i', 'em', 'u', 's', 'ul', 'ol', 'li', 'br',
        'p', 'blockquote', 'span', 'a', 'img', 'table', 'thead', 'tbody', 'tr', 'td', 'th'
    }

    ALLOWED_ATTRIBUTES = {
        'a': ['href', 'title', 'target'],
        'img': ['src', 'alt', 'title', 'class', 'style'],
        'span': ['style'],
        'p': ['style'],
        'td': ['colspan', 'rowspan'],
        'th': ['colspan', 'rowspan']
    }

    EMOJI_BASE_URL = "/static/emojis/"

    # Default case
    if not text:
        return ""

    # First decode HTML entities
    text = html.unescape(text)
    soup = BeautifulSoup(text, "html.parser")

    # Process all tags
    for tag in soup.find_all(True):
        if tag.name not in ALLOWED_TAGS:
            # Use unwrap instead of decompose to preserve content
            tag.unwrap()
            continue

        # Strip disallowed attributes
        allowed_attrs = ALLOWED_ATTRIBUTES.get(tag.name, [])
        attrs = dict(tag.attrs)
        for attr in list(attrs):
            if attr not in allowed_attrs:
                del tag.attrs[attr]

        # Keep only emoji <img> tags
        if tag.name == 'img':
            src = tag.get('src', '')
            if not (src.startswith(EMOJI_BASE_URL) or src.startswith('..' + EMOJI_BASE_URL)):
                tag.decompose()

    # Remove comments
    for comment in soup.find_all(string=lambda text: isinstance(text, Comment)):
        comment.extract()

    return str(soup)

def alphanumeric_text(text) -> str:
    return re.sub(r'[^a-zA-Z0-9-]', '', text)