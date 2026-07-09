import uuid

from airflow.hooks.postgres_hook import PostgresHook
from airflow.models import Variable
from openai import OpenAI
from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, PointStruct, VectorParams
from tqdm import tqdm

BATCH_SIZE = 50
QDRANT_COLLECTION_NAME = "wines_embeddings"


def run():
    # Load environment variables from Airflow Variables
    openai_api_key = Variable.get("OPENAI_API_KEY")
    qdrant_api_key = Variable.get("QDRANT_API_KEY")
    qdrant_host = Variable.get("QDRANT_HOST")

    if not all([openai_api_key, qdrant_api_key, qdrant_host]):
        raise ValueError("Missing one or more required environment variables.")

    # Set up OpenAI client
    openai_client = OpenAI(api_key=openai_api_key)

    # Set up Qdrant client
    qdrant_client = QdrantClient(
        url=qdrant_host,
        api_key=qdrant_api_key,
    )

    # Fetch wines to embed
    hook = PostgresHook(postgres_conn_id="postgres_godvinkaup")
    pg_conn = hook.get_conn()
    cursor = pg_conn.cursor()

    cursor.execute("""
        SELECT
            pk_wine,
            text_to_embed,
            wine_name,
            volume,
            price,
            country,
            origin_place,
            origin_district,
            grapes,
            produced_year,
            category,
            producer,
            seller,
            seller_link,
            link_vivino,
            recommendation,
            image_url_use,
            rating,
            rating_count
        FROM marts.wines_to_embed
        WHERE recommendation >= 0.5
    """)
    rows = cursor.fetchall()

    print(f"Fetched {len(rows)} wines to embed.")
    if not rows:
        return

    ids = [row[0] for row in rows]
    texts = [row[1] for row in rows]
    metadata = [row[2:] for row in rows]

    # Generate a test embedding to get dimensionality
    print("Generating sample embedding to detect dimensions...")
    test_embed = (
        openai_client.embeddings.create(input=[texts[0]], model="text-embedding-3-small")
        .data[0]
        .embedding
    )
    dimensions = len(test_embed)
    print(f"Detected embedding dimension: {dimensions}")

    # Create collection if it doesn’t exist
    existing_collections = [col.name for col in qdrant_client.get_collections().collections]
    if QDRANT_COLLECTION_NAME not in existing_collections:
        print(f"Creating Qdrant collection: {QDRANT_COLLECTION_NAME}")
        qdrant_client.recreate_collection(
            collection_name=QDRANT_COLLECTION_NAME,
            vectors_config=VectorParams(size=dimensions, distance=Distance.COSINE),
        )
        print(f"Collection '{QDRANT_COLLECTION_NAME}' created.")
    else:
        print(f"Collection '{QDRANT_COLLECTION_NAME}' already exists.")

    # Embed and upsert in batches
    for i in tqdm(range(0, len(texts), BATCH_SIZE)):
        batch_ids = ids[i : i + BATCH_SIZE]
        batch_texts = texts[i : i + BATCH_SIZE]
        batch_meta = metadata[i : i + BATCH_SIZE]

        embeddings = openai_client.embeddings.create(
            input=batch_texts, model="text-embedding-3-small"
        ).data

        points = [
            PointStruct(
                id=str(uuid.uuid5(uuid.NAMESPACE_DNS, f"wine-{batch_ids[j]}")),
                vector=embeddings[j].embedding,
                payload={
                    "pk_wine": batch_ids[j],
                    "wine_name": batch_meta[j][0],
                    "volume": batch_meta[j][1],
                    "price": float(batch_meta[j][2]),
                    "country": batch_meta[j][3],
                    "origin_place": batch_meta[j][4],
                    "origin_district": batch_meta[j][5],
                    "grapes": batch_meta[j][6],
                    "produced_year": batch_meta[j][7],
                    "category": batch_meta[j][8],
                    "producer": batch_meta[j][9],
                    "seller": batch_meta[j][10],
                    "seller_link": batch_meta[j][11],
                    "link_vivino": batch_meta[j][12],
                    "recommendation": float(batch_meta[j][13]),
                    "image_url": batch_meta[j][14],
                    "rating": batch_meta[j][15],
                    "rating_count": batch_meta[j][16],
                },
            )
            for j in range(len(batch_ids))
        ]

        try:
            qdrant_client.upsert(collection_name=QDRANT_COLLECTION_NAME, points=points)
        except Exception as e:
            print(f"Qdrant upsert error: {e}")
