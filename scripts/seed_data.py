#!/usr/bin/env python3
"""
Script de Geração e Inserção de Dados - Catálogo de Produtos E-commerce
Gera 100.000+ documentos realistas no MongoDB

Autor: Trabalho SGBD II - 2025/2026
Requisitos: pip install pymongo faker tqdm
"""

import random
import time
import socket
from datetime import datetime, timedelta
from pymongo import MongoClient, ASCENDING, DESCENDING, TEXT, GEOSPHERE
from pymongo.errors import BulkWriteError
from faker import Faker
from tqdm import tqdm
import json

# ──────────────────────────────────────────────
# CONFIGURAÇÃO — detecta automaticamente o ambiente
# ──────────────────────────────────────────────
def get_mongo_uri():
    """Detecta automaticamente a melhor URI para ligar ao MongoDB"""
    # Tenta primeiro com Replica Set (ideal)
    uris = [
        "mongodb://mongo1:27017,mongo2:27017,mongo3:27017/?replicaSet=rs0",
        "mongodb://localhost:27017/?replicaSet=rs0",
        "mongodb://localhost:27017/?directConnection=true",
        "mongodb://localhost:27017/",
    ]
    for uri in uris:
        try:
            c = MongoClient(uri, serverSelectionTimeoutMS=3000)
            c.admin.command('ping')
            c.close()
            return uri
        except:
            continue
    return "mongodb://localhost:27017/"

MONGO_URI = get_mongo_uri()
DB_NAME = "ecommerce_catalog"
BATCH_SIZE = 1000
TOTAL_PRODUCTS = 100_000
TOTAL_USERS = 10_000
TOTAL_REVIEWS = 200_000

fake = Faker('pt_PT')
Faker.seed(42)
random.seed(42)

# ──────────────────────────────────────────────
# DADOS DE REFERÊNCIA
# ──────────────────────────────────────────────
CATEGORIES = {
    "Eletrónicos": {
        "subcategories": ["Smartphones", "Laptops", "Tablets", "Auscultadores", "Smartwatches", "Câmaras"],
        "brands": ["Samsung", "Apple", "Xiaomi", "Sony", "LG", "Huawei", "Lenovo", "Asus"],
        "price_range": (44100, 3150000),
        "attributes": {
            "Smartphones": ["RAM", "Armazenamento", "Ecrã", "Bateria", "SO", "Câmara"],
            "Laptops": ["Processador", "RAM", "SSD", "Ecrã", "Placa Gráfica", "SO", "Bateria"],
            "Tablets": ["RAM", "Armazenamento", "Ecrã", "Bateria", "Conectividade"],
            "Auscultadores": ["Tipo", "Conectividade", "Cancelamento Ruído", "Bateria"],
            "Smartwatches": ["Ecrã", "Bateria", "GPS", "Impermeabilidade", "SO"],
            "Câmaras": ["Megapixeis", "Zoom", "Estabilização", "Resolução Vídeo", "Tipo"],
        }
    },
    "Moda": {
        "subcategories": ["T-shirts", "Calças", "Vestidos", "Sapatos", "Casacos", "Acessórios"],
        "brands": ["Zara", "H&M", "Nike", "Adidas", "Pull&Bear", "Bershka", "Massimo Dutti"],
        "price_range": (4500, 450000),
        "attributes": {
            "T-shirts": ["Tamanho", "Material", "Género", "Manga"],
            "Calças": ["Tamanho", "Material", "Corte", "Género"],
            "Vestidos": ["Tamanho", "Material", "Comprimento", "Ocasião"],
            "Sapatos": ["Tamanho", "Material", "Género", "Tipo"],
            "Casacos": ["Tamanho", "Material", "Género", "Fecho"],
            "Acessórios": ["Tipo", "Material", "Género"],
        }
    },
    "Casa & Jardim": {
        "subcategories": ["Móveis", "Decoração", "Cozinha", "Jardim", "Iluminação", "Têxteis"],
        "brands": ["IKEA", "Leroy Merlin", "El Corte Inglés", "Casa", "Zara Home"],
        "price_range": (9000, 1800000),
        "attributes": {
            "Móveis": ["Material", "Dimensões", "Cor", "Estilo"],
            "Decoração": ["Material", "Dimensões", "Cor", "Estilo"],
            "Cozinha": ["Material", "Capacidade", "Compatibilidade", "Cor"],
            "Jardim": ["Material", "Dimensões", "Para exterior"],
            "Iluminação": ["Potência", "Tipo lâmpada", "Cor luz", "IP"],
            "Têxteis": ["Material", "Dimensões", "Cor", "Cuidados"],
        }
    },
    "Desporto": {
        "subcategories": ["Fitness", "Ciclismo", "Natação", "Running", "Futebol", "Ténis"],
        "brands": ["Nike", "Adidas", "Decathlon", "Under Armour", "Salomon", "Garmin"],
        "price_range": (9000, 1080000),
        "attributes": {
            "Fitness": ["Peso máximo", "Material", "Dimensões", "Tipo"],
            "Ciclismo": ["Tamanho quadro", "Material", "Velocidades", "Tipo travão"],
            "Running": ["Tamanho", "Género", "Drop", "Pisada"],
        }
    },
    "Livros & Media": {
        "subcategories": ["Livros", "Música", "Filmes", "Jogos", "E-books"],
        "brands": ["Bertrand", "Porto Editora", "Fnac", "Amazon", "Steam"],
        "price_range": (4500, 108000),
        "attributes": {
            "Livros": ["Autor", "Editora", "Ano", "Páginas", "ISBN", "Idioma"],
            "Jogos": ["Plataforma", "Classificação etária", "Género", "Multijogador"],
        }
    }
}

WAREHOUSES = [
    {"id": "WH-LUA-01", "city": "Luanda",    "lat": -8.8390,  "lon": 13.2894},
    {"id": "WH-HUA-01", "city": "Huambo",    "lat": -12.7756, "lon": 15.7390},
    {"id": "WH-LOB-01", "city": "Lobito",    "lat": -12.3647, "lon": 13.5456},
    {"id": "WH-BEN-01", "city": "Benguela",  "lat": -12.5763, "lon": 13.4055},
    {"id": "WH-MAL-01", "city": "Malanje",   "lat": -9.5400,  "lon": 16.3410},
]

TAGS_POOL = [
    "bestseller", "novidade", "promoção", "exclusivo", "eco-friendly",
    "premium", "edição-limitada", "importado", "nacional", "certificado",
    "tecnologia", "design", "conforto", "durabilidade", "leveza"
]


def generate_attributes(category_name, subcategory):
    cat = CATEGORIES.get(category_name, {})
    attr_keys = cat.get("attributes", {}).get(subcategory, ["Cor", "Material", "Peso"])
    attr_map = {
        "RAM": random.choice(["4GB", "6GB", "8GB", "12GB", "16GB", "32GB"]),
        "Armazenamento": random.choice(["32GB", "64GB", "128GB", "256GB", "512GB", "1TB"]),
        "SSD": random.choice(["128GB", "256GB", "512GB", "1TB", "2TB"]),
        "Ecrã": random.choice(["5.5\"", "6.1\"", "6.4\"", "6.7\"", "13.3\"", "14\"", "15.6\""]),
        "Bateria": f"{random.randint(2000, 6000)} mAh",
        "SO": random.choice(["Android 14", "iOS 17", "Windows 11", "macOS Sonoma"]),
        "Câmara": f"{random.choice([12, 48, 50, 108, 200])} MP",
        "Processador": random.choice(["Intel i5-13ª", "Intel i7-13ª", "AMD Ryzen 5", "AMD Ryzen 7", "Apple M3"]),
        "Placa Gráfica": random.choice(["Integrada", "NVIDIA RTX 4060", "NVIDIA RTX 4070", "AMD RX 7600"]),
        "Tipo": random.choice(["Over-ear", "In-ear", "On-ear", "True Wireless"]),
        "Conectividade": random.choice(["Bluetooth 5.3", "Wi-Fi 6E", "USB-C", "Jack 3.5mm"]),
        "Cancelamento Ruído": random.choice(["ANC", "Passivo", "Híbrido"]),
        "GPS": random.choice([True, False]),
        "Impermeabilidade": random.choice(["IP67", "IP68", "5ATM", "IP44"]),
        "Megapixeis": random.choice([12, 20, 24, 48, 61]),
        "Zoom": f"{random.randint(3, 30)}x",
        "Estabilização": random.choice(["Ótica (OIS)", "Digital (EIS)", "Híbrida"]),
        "Resolução Vídeo": random.choice(["4K 60fps", "4K 30fps", "1080p 120fps"]),
        "Tamanho": random.choice(["XS", "S", "M", "L", "XL", "XXL", "36", "38", "40", "42", "44"]),
        "Material": random.choice(["Algodão", "Poliéster", "Linho", "Madeira", "Metal", "Couro"]),
        "Género": random.choice(["Masculino", "Feminino", "Unissex"]),
        "Manga": random.choice(["Curta", "Longa", "Sem manga"]),
        "Corte": random.choice(["Slim", "Regular", "Wide", "Skinny", "Straight"]),
        "Comprimento": random.choice(["Mini", "Médio", "Maxi"]),
        "Ocasião": random.choice(["Casual", "Formal", "Desportivo", "Festa"]),
        "Fecho": random.choice(["Botões", "Fecho éclair", "Velcro"]),
        "Cor": random.choice(["Preto", "Branco", "Azul", "Vermelho", "Verde", "Cinza"]),
        "Estilo": random.choice(["Moderno", "Clássico", "Rústico", "Industrial", "Escandinavo"]),
        "Dimensões": f"{random.randint(20,200)}x{random.randint(20,200)}x{random.randint(5,100)} cm",
        "Capacidade": f"{random.choice([1, 2, 5, 10, 15, 20, 50])} L",
        "Compatibilidade": random.choice(["Universal", "Indução", "Vitrocerâmica", "Gás"]),
        "Para exterior": random.choice([True, False]),
        "Potência": f"{random.choice([7, 9, 15, 25, 40, 60, 100])}W",
        "Tipo lâmpada": random.choice(["LED", "E27", "GU10", "E14"]),
        "Cor luz": random.choice(["Quente 2700K", "Neutra 4000K", "Fria 6500K", "RGB"]),
        "IP": random.choice(["IP20", "IP44", "IP65", "IP68"]),
        "Cuidados": random.choice(["Lavagem 30°", "Lavagem 60°", "Lavar à mão"]),
        "Peso máximo": f"{random.choice([50, 80, 100, 120, 150, 200])} kg",
        "Velocidades": random.choice(["7", "11", "21", "27"]),
        "Tipo travão": random.choice(["V-brake", "Disco mecânico", "Disco hidráulico"]),
        "Drop": f"{random.choice([0, 4, 6, 8, 10, 12])} mm",
        "Pisada": random.choice(["Neutra", "Pronação", "Supinação"]),
        "Autor": fake.name(),
        "Editora": random.choice(["Porto Editora", "Bertrand", "Presença", "Leya"]),
        "Ano": str(random.randint(1990, 2024)),
        "Páginas": str(random.randint(100, 1200)),
        "ISBN": f"978-{random.randint(100,999)}-{random.randint(10000,99999)}-{random.randint(10,99)}-{random.randint(0,9)}",
        "Idioma": random.choice(["Português", "Inglês", "Espanhol"]),
        "Plataforma": random.choice(["PC", "PlayStation 5", "Xbox Series X", "Nintendo Switch"]),
        "Classificação etária": random.choice(["3+", "7+", "12+", "16+", "18+"]),
        "Multijogador": random.choice([True, False]),
    }
    return {k: attr_map.get(k, fake.word()) for k in attr_keys}


def generate_price_history(current_price):
    history = []
    price = current_price * random.uniform(1.1, 1.5)
    for i in range(random.randint(3, 12)):
        price = price * random.uniform(0.85, 1.15)
        history.append({
            "date": datetime.now() - timedelta(days=random.randint(1, 365)),
            "price": round(max(price, 900), 2),
            "reason": random.choice(["Promoção", "Reajuste", "Black Friday", "Saldo", "Retorno normal"])
        })
    return sorted(history, key=lambda x: x["date"])


def generate_warehouse_stock():
    warehouses = random.sample(WAREHOUSES, k=random.randint(1, len(WAREHOUSES)))
    return [
        {
            "warehouse_id": wh["id"],
            "city": wh["city"],
            "quantity": random.randint(0, 500),
            "location": {
                "type": "Point",
                "coordinates": [wh["lon"], wh["lat"]]
            }
        }
        for wh in warehouses
    ]


def generate_product(product_id: int) -> dict:
    cat_name = random.choice(list(CATEGORIES.keys()))
    cat = CATEGORIES[cat_name]
    subcategory = random.choice(cat["subcategories"])
    brand = random.choice(cat["brands"])
    price_min, price_max = cat["price_range"]
    price = round(random.uniform(price_min, price_max), 2)
    avg_rating = round(random.uniform(1.0, 5.0), 1)
    total_reviews = random.randint(0, 5000)
    num_skus = random.randint(1, 5)
    skus = []
    for i in range(num_skus):
        sku_price = round(price * random.uniform(0.9, 1.3), 2)
        skus.append({
            "sku_id": f"SKU-{product_id:06d}-{i:02d}",
            "variant": f"Variante {chr(65+i)}",
            "price": sku_price,
            "stock": random.randint(0, 200),
            "barcode": f"{random.randint(1000000000000, 9999999999999)}"
        })
    total_stock = sum(s["stock"] for s in skus)
    created_at = datetime.now() - timedelta(days=random.randint(0, 1095))
    return {
        "product_id": f"PROD-{product_id:06d}",
        "ean": f"{random.randint(1000000000000, 9999999999999)}",
        "name": f"{brand} {subcategory} {fake.word().capitalize()} {random.randint(1,9999)}",
        "brand": brand,
        "category": cat_name,
        "subcategory": subcategory,
        "description": fake.paragraph(nb_sentences=5),
        "short_description": fake.sentence(nb_words=15),
        "price": price,
        "currency": "AOA",
        "discount_percentage": random.choice([0, 0, 0, 5, 10, 15, 20, 25, 30, 40, 50]),
        "price_history": generate_price_history(price),
        "ratings_summary": {
            "average": avg_rating,
            "total_reviews": total_reviews,
            "distribution": {
                "5": int(total_reviews * random.uniform(0.3, 0.6)),
                "4": int(total_reviews * random.uniform(0.1, 0.3)),
                "3": int(total_reviews * random.uniform(0.05, 0.15)),
                "2": int(total_reviews * random.uniform(0.02, 0.08)),
                "1": int(total_reviews * random.uniform(0.01, 0.05)),
            }
        },
        "attributes": generate_attributes(cat_name, subcategory),
        "tags": random.sample(TAGS_POOL, k=random.randint(1, 6)),
        "search_keywords": [
            cat_name.lower(), subcategory.lower(), brand.lower(),
            *[fake.word() for _ in range(random.randint(2, 5))]
        ],
        "skus": skus,
        "total_stock": total_stock,
        "in_stock": total_stock > 0,
        "warehouse_stock": generate_warehouse_stock(),
        "images": [
            {"url": f"https://cdn.ecommerce.ao/products/{product_id:06d}/img_{j}.webp",
             "is_primary": j == 0,
             "alt": f"{brand} {subcategory} imagem {j+1}"}
            for j in range(random.randint(1, 6))
        ],
        "status": random.choice(["active", "active", "active", "inactive", "discontinued"]),
        "is_featured": random.random() < 0.05,
        "created_at": created_at,
        "updated_at": created_at + timedelta(days=random.randint(0, 100)),
        "seller_id": f"SELLER-{random.randint(1, 500):04d}",
        "views_count": random.randint(0, 100000),
        "sales_count": random.randint(0, 10000),
        "related_product_ids": [
            f"PROD-{random.randint(1, TOTAL_PRODUCTS):06d}"
            for _ in range(random.randint(0, 5))
        ],
    }


def generate_user(user_id: int) -> dict:
    created = datetime.now() - timedelta(days=random.randint(0, 1825))
    return {
        "user_id": f"USER-{user_id:05d}",
        "username": fake.user_name(),
        "email": fake.email(),
        "name": fake.name(),
        "segment": random.choice(["bronze", "silver", "gold", "platinum"]),
        "location": {
            "city": random.choice(["Luanda", "Huambo", "Lobito", "Benguela", "Malanje", "Lubango"]),
            "country": "AO",
            "coordinates": {
                "type": "Point",
                "coordinates": [
                    round(random.uniform(11.7, 24.1), 4),
                    round(random.uniform(-18.0, -4.4), 4)
                ]
            }
        },
        "preferences": {
            "favorite_categories": random.sample(list(CATEGORIES.keys()), k=random.randint(1, 3)),
            "newsletter": random.choice([True, False]),
            "language": random.choice(["pt", "en"])
        },
        "total_orders": random.randint(0, 200),
        "total_spent": round(random.uniform(0, 13500000), 2),
        "created_at": created,
        "last_login": created + timedelta(days=random.randint(0, 365)),
    }


def generate_review(review_id: int, product_ids: list, user_ids: list) -> dict:
    rating = random.choices([1, 2, 3, 4, 5], weights=[5, 5, 15, 35, 40])[0]
    created = datetime.now() - timedelta(days=random.randint(0, 730))
    sentiments = {
        5: ["Excelente produto!", "Muito satisfeito!", "Recomendo vivamente!"],
        4: ["Bom produto.", "Satisfeito com a compra.", "Boa relação qualidade-preço."],
        3: ["Produto razoável.", "Esperava mais.", "Cumpre o básico."],
        2: ["Decepcionante.", "Não recomendo.", "Qualidade abaixo do esperado."],
        1: ["Péssimo produto!", "Não funciona.", "Devolvi o produto."],
    }
    return {
        "review_id": f"REV-{review_id:07d}",
        "product_id": random.choice(product_ids),
        "user_id": random.choice(user_ids),
        "rating": rating,
        "title": random.choice(sentiments[rating]),
        "body": fake.paragraph(nb_sentences=random.randint(1, 5)),
        "verified_purchase": random.choice([True, True, False]),
        "helpful_votes": random.randint(0, 500),
        "created_at": created,
        "images": [
            f"https://cdn.ecommerce.ao/reviews/{review_id:07d}/img_{j}.webp"
            for j in range(random.randint(0, 3))
        ],
    }


def create_indexes(db):
    print("\n📑 Criando índices otimizados...")
    products = db.products
    products.create_index([("category", ASCENDING), ("price", ASCENDING)], name="idx_category_price")
    products.create_index([("brand", ASCENDING), ("subcategory", ASCENDING)], name="idx_brand_subcategory")
    products.create_index([("price", ASCENDING), ("ratings_summary.average", DESCENDING)], name="idx_price_rating")
    products.create_index([("status", ASCENDING), ("in_stock", ASCENDING), ("is_featured", DESCENDING)], name="idx_status_stock_featured")
    products.create_index(
        [("name", TEXT), ("description", TEXT), ("search_keywords", TEXT), ("brand", TEXT)],
        name="idx_text_search",
        weights={"name": 10, "brand": 8, "search_keywords": 5, "description": 1}
    )
    products.create_index([("warehouse_stock.location", GEOSPHERE)], name="idx_warehouse_geo")
    products.create_index([("views_count", DESCENDING)], name="idx_views")
    products.create_index([("sales_count", DESCENDING)], name="idx_sales")
    products.create_index([("ratings_summary.average", DESCENDING), ("ratings_summary.total_reviews", DESCENDING)], name="idx_rating_reviews")
    products.create_index([("tags", ASCENDING)], name="idx_tags")
    products.create_index([("updated_at", ASCENDING)], name="idx_updated_at")
    db.reviews.create_index([("product_id", ASCENDING), ("rating", DESCENDING)], name="idx_review_product_rating")
    db.reviews.create_index([("user_id", ASCENDING)], name="idx_review_user")
    db.reviews.create_index([("created_at", DESCENDING)], name="idx_review_date")
    db.users.create_index([("email", ASCENDING)], unique=True, name="idx_user_email")
    db.users.create_index([("segment", ASCENDING)], name="idx_user_segment")
    print("✅ Índices criados com sucesso!")


def insert_batch(collection, documents: list):
    try:
        collection.insert_many(documents, ordered=False)
    except BulkWriteError as e:
        pass


def main():
    print("=" * 60)
    print("  SGBD II - Data Seeding: Catálogo E-commerce NoSQL")
    print("=" * 60)
    print(f"\n🔌 Conectando ao MongoDB: {MONGO_URI}")
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=8000)
    try:
        client.admin.command('ping')
        print("✅ Conexão estabelecida!")
    except Exception as e:
        print(f"❌ Erro de conexão: {e}")
        print("💡 Certifique-se que o Docker está a correr: docker-compose up -d")
        return
    db = client[DB_NAME]
    print("\n🗑️  Limpando dados anteriores...")
    db.products.drop(); db.users.drop(); db.reviews.drop()
    create_indexes(db)

    print(f"\n👥 Gerando {TOTAL_USERS:,} utilizadores...")
    batch = []; user_ids = []
    for i in tqdm(range(1, TOTAL_USERS + 1), desc="Utilizadores"):
        user = generate_user(i)
        user_ids.append(user["user_id"])
        batch.append(user)
        if len(batch) >= BATCH_SIZE:
            insert_batch(db.users, batch); batch = []
    if batch: insert_batch(db.users, batch)
    print(f"✅ Utilizadores inseridos!")

    print(f"\n📦 Gerando {TOTAL_PRODUCTS:,} produtos...")
    batch = []; product_ids = []
    start_time = time.time()
    for i in tqdm(range(1, TOTAL_PRODUCTS + 1), desc="Produtos"):
        product = generate_product(i)
        product_ids.append(product["product_id"])
        batch.append(product)
        if len(batch) >= BATCH_SIZE:
            insert_batch(db.products, batch); batch = []
    if batch: insert_batch(db.products, batch)
    elapsed = time.time() - start_time
    print(f"✅ {TOTAL_PRODUCTS:,} produtos inseridos em {elapsed:.1f}s!")

    print(f"\n⭐ Gerando {TOTAL_REVIEWS:,} avaliações...")
    batch = []
    for i in tqdm(range(1, TOTAL_REVIEWS + 1), desc="Avaliações"):
        review = generate_review(i, product_ids, user_ids)
        batch.append(review)
        if len(batch) >= BATCH_SIZE:
            insert_batch(db.reviews, batch); batch = []
    if batch: insert_batch(db.reviews, batch)
    print(f"✅ Avaliações inseridas!")

    print("\n" + "=" * 60)
    print("  SUMÁRIO FINAL DA BASE DE DADOS")
    print("=" * 60)
    total = 0
    for col in ["products", "users", "reviews"]:
        count = db[col].estimated_document_count()
        total += count
        print(f"  {col:15s}: {count:>10,} documentos")
    print(f"  {'TOTAL':15s}: {total:>10,} documentos")
    print("=" * 60)
    sample = db.products.find_one({}, {"_id": 0, "price_history": 0, "warehouse_stock": 0, "images": 0})
    print("\n📄 Exemplo de documento (produto):")
    print(json.dumps(sample, indent=2, default=str, ensure_ascii=False))
    client.close()
    print("\n🎉 Data seeding concluído com sucesso!")

if __name__ == "__main__":
    main()
