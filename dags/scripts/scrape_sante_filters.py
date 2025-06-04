import requests
from bs4 import BeautifulSoup
import psycopg2
import pandas as pd
import logging

# Set up logger
logging.basicConfig(
    format='%(asctime)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

def get_connection():
    """ Establish a connection to the PostgreSQL database """
    try:
        connection = psycopg2.connect(
            host='192.168.86.23',
            port='5433',
            database='godvinkaup',
            user='postgres',
            password='postgres'
        )
        connection.autocommit = True
        logger.info("✅ Database connection established.")
        return connection
    except Exception as e:
        logger.error(f"❌ Error connecting to database: {e}")
        raise

def recreate_staging_table(cursor) -> None:
    """ Drop and recreate the staging table """
    try:
        cursor.execute("""
            DROP TABLE IF EXISTS landing.sante_wine_filters CASCADE;
            CREATE UNLOGGED TABLE landing.sante_wine_filters (
                filter_name         TEXT,
                filter_key          TEXT,
                filter_value        TEXT
            );
            ALTER TABLE landing.sante_wine_filters ADD CONSTRAINT unique_filter UNIQUE (filter_key, filter_value);
        """)
        logger.info("✅ Staging table recreated.")
    except Exception as e:
        logger.error(f"❌ Error recreating staging table: {e}")
        raise

def insert_values(connection, records):
    """ Insert filter records into the database """
    try:
        # Convert to list of tuples (filter_name, filter_key, filter_value)
        values = [
            (r['filter_name'], r['filter_key'], r['filter_value'])
            for r in records
            if 'filter_name' in r and 'filter_key' in r and 'filter_value' in r
        ]

        with connection.cursor() as cursor:
            insert_query = """
                INSERT INTO landing.sante_wine_filters (filter_name, filter_key, filter_value)
                VALUES (%s, %s, %s)
                ON CONFLICT (filter_key, filter_value) DO NOTHING
            """
            cursor.executemany(insert_query, values)
            logger.info(f"✅ Inserted {cursor.rowcount} records into sante_wine_filters.")
    except Exception as e:
        logger.error(f"❌ Error inserting records: {e}")
        raise

def scrape_filters():
    """ Scrape filter data from the Shopify website """
    url = "https://sante.is/collections/lettvin"
    try:
        # Send a GET request to the URL
        response = requests.get(url)
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, "html.parser")
            list_items = soup.find_all(class_="list-menu__item facets__item")

            filter_records = []
            for item in list_items:
                input_tag = item.find('input')
                label_tag = item.find('label')

                if input_tag and label_tag:
                    name = input_tag.get('name')  # full filter name
                    label_text = label_tag.select_one('.facet-checkbox__text-label')
                    value = label_text.get_text(strip=True) if label_text else None

                    if name and value:
                        filter_key = name.rsplit('.', 1)[-1]

                        filter_records.append({
                            "filter_name": name,         # e.g., "filter.p.m.custom.flokkur"
                            "filter_key": filter_key,    # e.g., "flokkur"
                            "filter_value": value        # e.g., "Rauðvín"
                        })

            logger.info(f"✅ Scraped {len(filter_records)} filter records.")
            return filter_records
        else:
            logger.error(f"❌ Failed to retrieve the page, status code: {response.status_code}")
            return []
    except Exception as e:
        logger.error(f"❌ Error scraping filters: {e}")
        raise

def run():
    """ Main function to orchestrate the process """
    logger.info("✅ Starting the process...")
    connection = get_connection()

    try:
        with connection.cursor() as cursor:
            recreate_staging_table(cursor)

        filter_records = scrape_filters()

        if filter_records:
            insert_values(connection, filter_records)
        else:
            logger.warning("No filter records to insert.")
    
    finally:
        connection.close()
        logger.info("✅ Connection closed.")

if __name__ == "__main__":
    run()
