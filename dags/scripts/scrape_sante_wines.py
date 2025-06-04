import requests
from bs4 import BeautifulSoup
import re
import pandas as pd
import psycopg2
import datetime

# Database connection
connection = psycopg2.connect(
    host='192.168.86.23',
    port='5433',
    database='godvinkaup',
    user='postgres',
    password='postgres',
)
connection.autocommit = True

insert_date = datetime.date.today()
currentYear = insert_date.year

# Map of known regions to countries
wine_country_map = {
    # Argentína
    "Mendoza": "Argentína",

    # Ástralía
    "Barossa": "Ástralía",
    "Tasmania": "Ástralía",

    # Frakkland
    "Bordeaux": "Frakkland",
    "Bourgogne": "Frakkland",
    "Castillon": "Frakkland",
    "Chateau": "Frakkland",
    "Champagne": "Frakkland",
    "Drappier": "Frakkland",
    "Provence": "Frakkland",
    "Saint-Emilion": "Frakkland",

    # Ítalía
    "Barbera": "Ítalía",
    "Barolo": "Ítalía",
    "Chianti": "Ítalía",
    "Nebbiolo": "Ítalía",
    "Piedmont": "Ítalía",
    "Sicily": "Ítalía",
    "Tuscany": "Ítalía",

    # Nýja-Sjáland
    "Marlborough": "Nýja-Sjáland",

    # Spánn
    "Alejairen": "Spánn",
    "Cava": "Spánn",
    "Izadi": "Spánn",
    "Rioja": "Spánn",

    # USA
    "Napa": "USA",
    "Sonoma": "USA"
}


def recreate_staging_table(cursor) -> None:
    cursor.execute("""
        DROP TABLE IF EXISTS landing.sante_wines CASCADE; 
        CREATE UNLOGGED TABLE landing.sante_wines (
            id                      TEXT,
            name                    TEXT,
            produced_year           INTEGER,
            producer                TEXT,
            type                    TEXT,
            price                   DECIMAL,
            size                    INT,
            available               TEXT,
            product_url             TEXT,
            image_url               TEXT,
            first_sale_date         DATE,
            country                 TEXT,
            area                    TEXT,
            grapes                  TEXT,
            district                TEXT,
            batch_date              DATE
        );
    """)


def insert_wines(connection, wines) -> None:
    insert_query = '''INSERT INTO landing.sante_wines 
    (id, name, produced_year, producer, type, price, size, available, product_url, image_url, first_sale_date, country, area, grapes, district, batch_date)
    VALUES(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s);'''

    with connection.cursor() as cursor:
        cursor.executemany(insert_query, wines)


def get_filter_values(connection, filter_name) -> list:
    query = f"SELECT filter_value FROM landing.sante_wine_filters WHERE filter_key = '{filter_name}'"
    with connection.cursor() as cursor:
        cursor.execute(query)
        result = cursor.fetchall()
        return [item[0] for item in result]


def run():
    with connection.cursor() as cursor:
        recreate_staging_table(cursor)

    country_list = get_filter_values(connection, 'upprunaland')
    area_list = get_filter_values(connection, 'herad')
    grapes_list = get_filter_values(connection, 'thrug%')
    district_list = get_filter_values(connection, 'thorp')

    link = 'https://sante.is/collections/lettvin/products.json?limit=1000'
    raw_data = requests.get(link)
    data = raw_data.json()["products"]
    link_prefix = 'https://sante.is/products/'

    wines_to_insert = []

    for product in data:
        pid = product["id"]
        title_raw = product["title"]
        cl_pos = title_raw.find('cl.')
        if cl_pos != -1:
            find_rspace = title_raw[:cl_pos - 1].rfind(' ')
            title = title_raw[:find_rspace]
        else:
            title = title_raw

        producer = product["vendor"]
        wine_type = product["product_type"]
        image_url = product["images"][0]["src"]
        created_at = product["created_at"]

        product_price = product["variants"][0]["price"]
        product_available = product["variants"][0]["available"]

        product_handle = product["handle"]
        product_url = link_prefix + product_handle

        tags = product["tags"]

        # Produced year
        produced_year = 0
        year_match = re.match(r"^(\d{4})", title_raw)
        if year_match:
            produced_year = int(year_match.group(1))
        else:
            for tag in tags:
                try:
                    possible_year = int(tag)
                    if (currentYear - possible_year < 30):
                        produced_year = possible_year
                except ValueError:
                    continue

        # Size in ml
        product_size = next((
            int(float(tag.replace('cl', '').strip()) * 10)
            for tag in tags 
            if 'cl' in tag and tag.replace('cl', '').strip().replace('.', '', 1).isdigit()
        ), 0)

        # Country
        country = next((tag for tag in tags if tag in country_list), 'N/F')
        if country == 'N/F':
            title_lower = title_raw.lower()
            for region, inferred_country in wine_country_map.items():
                if region.lower() in title_lower:
                    country = inferred_country
                    break

        area = next((tag for tag in tags if tag in area_list), 'N/F')
        grapes_l = [tag for tag in tags if tag in grapes_list]
        grapes = ",".join(grapes_l)
        district = next((tag for tag in tags if tag in district_list), 'N/F')

        result = (
            pid, title, produced_year, producer, wine_type, product_price, product_size,
            product_available, product_url, image_url, created_at,
            country, area, grapes, district, insert_date
        )
        wines_to_insert.append(result)

    try:
        insert_wines(connection, wines_to_insert)
        print(f"{len(wines_to_insert)} wines added to landing.sante_wines")
    except Exception as e:
        print('Error inserting into landing table:', e)


if __name__ == "__main__":
    run()
