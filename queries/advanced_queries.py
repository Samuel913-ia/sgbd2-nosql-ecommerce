#!/usr/bin/env python3
"""
Script de Consultas Avançadas - Catálogo de Produtos E-commerce
7 consultas complexas com MongoDB Aggregation Pipeline

Autor: Trabalho SGBD II - 2025/2026
Requisitos: pip install pymongo tabulate
"""

import time
from datetime import datetime, timedelta
from pymongo import MongoClient
from tabulate import tabulate

# ── Detecção automática da URI ─────────────────────────────────────────────
def get_mongo_uri():
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
DB_NAME   = "ecommerce_catalog"
client    = MongoClient(MONGO_URI, serverSelectionTimeoutMS=8000)
db        = client[DB_NAME]

def run_query(name, fn):
    print(f"\n{'='*70}")
    print(f"  {name}")
    print(f"{'='*70}")
    start = time.perf_counter()
    result = fn()
    elapsed_ms = (time.perf_counter() - start) * 1000
    print(f"\n⏱  Tempo de execução: {elapsed_ms:.2f} ms")
    return result, elapsed_ms

# ══════════════════════════════════════════════════════════════════════════════
# Q1 — Pesquisa Facetada com múltiplos filtros
# ══════════════════════════════════════════════════════════════════════════════
def query1_faceted_search():
    pipeline = [
        {"$match": {"category": "Eletrónicos", "price": {"$gte": 90000, "$lte": 720000},
                    "in_stock": True, "status": "active", "ratings_summary.average": {"$gte": 3.5}}},
        {"$facet": {
            "products": [
                {"$sort": {"ratings_summary.average": -1, "sales_count": -1}},
                {"$limit": 10},
                {"$project": {"_id":0,"product_id":1,"name":1,"brand":1,"subcategory":1,
                               "price":1,"discount_percentage":1,"ratings_summary":1,"total_stock":1}}
            ],
            "subcategory_counts": [
                {"$group": {"_id": "$subcategory", "count": {"$sum": 1}}},
                {"$sort": {"count": -1}}
            ],
            "brand_counts": [
                {"$group": {"_id": "$brand", "count": {"$sum": 1}}},
                {"$sort": {"count": -1}}, {"$limit": 10}
            ],
            "price_stats": [
                {"$group": {"_id": None, "min_price": {"$min": "$price"},
                            "max_price": {"$max": "$price"}, "avg_price": {"$avg": "$price"},
                            "total_results": {"$sum": 1}}}
            ]
        }}
    ]
    result = list(db.products.aggregate(pipeline))[0]
    stats = result['price_stats'][0]
    print(f"\n Total: {stats['total_results']:,} produtos")
    print(f"   Preço mínimo: Kz {stats['min_price']:,.0f}")
    print(f"   Preço máximo: Kz {stats['max_price']:,.0f}")
    print(f"   Preço médio:  Kz {stats['avg_price']:,.0f}")
    print("\n Por Subcategoria:")
    print(tabulate([[r["_id"], r["count"]] for r in result["subcategory_counts"]],
                   headers=["Subcategoria", "Produtos"], tablefmt="simple"))
    print("\n Top 5 Produtos:")
    print(tabulate([[p["product_id"], p["name"][:35], p["brand"],
                     f"Kz {p['price']:,.0f}", p["ratings_summary"]["average"]]
                    for p in result["products"][:5]],
                   headers=["ID", "Nome", "Marca", "Preço (AOA)", "Rating"], tablefmt="simple"))
    return result

# ══════════════════════════════════════════════════════════════════════════════
# Q2 — Análise de Receita por Categoria
# ══════════════════════════════════════════════════════════════════════════════
def query2_category_revenue():
    pipeline = [
        {"$match": {"status": "active"}},
        {"$group": {
            "_id": "$category",
            "total_products": {"$sum": 1},
            "total_stock_value": {"$sum": {"$multiply": ["$price", "$total_stock"]}},
            "avg_price": {"$avg": "$price"},
            "avg_rating": {"$avg": "$ratings_summary.average"},
            "total_sales": {"$sum": "$sales_count"},
        }},
        {"$sort": {"total_stock_value": -1}}
    ]
    results = list(db.products.aggregate(pipeline))
    print("\n💰 Receita Potencial por Categoria (AOA):")
    print(tabulate([[r["_id"], f"{r['total_products']:,}",
                     f"Kz {r['total_stock_value']:,.0f}", f"{r['total_sales']:,}"]
                    for r in results],
                   headers=["Categoria", "Produtos", "Valor Stock (AOA)", "Vendas Total"],
                   tablefmt="grid"))
    return results

# ══════════════════════════════════════════════════════════════════════════════
# Q3 — Pesquisa Full-Text com Score Composto
# ══════════════════════════════════════════════════════════════════════════════
def query3_fulltext_search():
    search_term = "laptop gaming"
    pipeline = [
        {"$match": {"$text": {"$search": search_term}, "status": "active", "in_stock": True}},
        {"$addFields": {
            "text_score": {"$meta": "textScore"},
            "composite_score": {"$add": [
                {"$multiply": [{"$meta": "textScore"}, 10]},
                {"$multiply": [{"$divide": ["$ratings_summary.average", 5]}, 3]},
                {"$multiply": [{"$divide": ["$sales_count", {"$add": ["$sales_count", 1000]}]}, 2]}
            ]}
        }},
        {"$sort": {"composite_score": -1}},
        {"$limit": 10},
        {"$project": {"_id":0,"product_id":1,"name":1,"brand":1,"price":1,
                       "composite_score":{"$round":["$composite_score",3]},
                       "ratings_summary.average":1}}
    ]
    results = list(db.products.aggregate(pipeline))
    print(f"\n🔍 Resultados para: '{search_term}'")
    print(tabulate([[r["product_id"], r["name"][:35], r["brand"],
                     f"Kz {r['price']:,.0f}", r["ratings_summary"]["average"],
                     r["composite_score"]]
                    for r in results],
                   headers=["ID", "Nome", "Marca", "Preço (AOA)", "Rating", "Score"],
                   tablefmt="simple"))
    return results

# ══════════════════════════════════════════════════════════════════════════════
# Q4 — Atualização Parcial Complexa (Arrays)
# ══════════════════════════════════════════════════════════════════════════════
def query4_complex_update():
    product = db.products.find_one(
        {"status": "active", "in_stock": True, "category": "Eletrónicos"},
        {"product_id":1, "name":1, "price":1}
    )
    if not product:
        print(" Produto não encontrado"); return None
    product_id = product["product_id"]
    old_price   = product["price"]
    new_price   = round(old_price * 0.80, 2)
    print(f"\n🔧 Produto: {product_id}")
    print(f"   Preço antigo: Kz {old_price:,.0f}")
    print(f"   Novo preço:   Kz {new_price:,.0f} (-20%)")
    result = db.products.update_one(
        {"product_id": product_id},
        {
            "$set": {"price": new_price, "discount_percentage": 20, "updated_at": datetime.now()},
            "$push": {"price_history": {"date": datetime.now(), "price": new_price, "reason": "Promoção Flash -20%"}},
            "$addToSet": {"tags": "promoção"},
            "$inc": {"update_count": 1}
        }
    )
    updated = db.products.find_one({"product_id": product_id},
        {"_id":0,"price":1,"tags":1,"discount_percentage":1,"price_history":{"$slice":-2}})
    print(f"\n Modificado: {result.modified_count} documento")
    print(f"   Tags: {updated.get('tags', [])}")
    print(f"   Últimas entradas do price_history:")
    for ph in updated.get("price_history", []):
        date_str = ph['date'].strftime('%Y-%m-%d') if isinstance(ph['date'], datetime) else str(ph['date'])
        print(f"     - Kz {ph['price']:,.0f} ({ph.get('reason','')}) em {date_str}")
    return result

# ══════════════════════════════════════════════════════════════════════════════
# Q5 — Consulta Geoespacial: Produtos perto de Luanda
# ══════════════════════════════════════════════════════════════════════════════
def query5_geospatial():
    LUANDA_LNG = 13.2894
    LUANDA_LAT = -8.8390
    RADIUS_KM  = 200
    pipeline = [
        {"$match": {
            "status": "active", "in_stock": True,
            "warehouse_stock": {
                "$elemMatch": {
                    "location": {"$geoWithin": {"$centerSphere": [[LUANDA_LNG, LUANDA_LAT], RADIUS_KM/6371]}},
                    "quantity": {"$gt": 0}
                }
            }
        }},
        {"$addFields": {
            "nearby_warehouses": {
                "$filter": {"input": "$warehouse_stock", "as": "wh",
                            "cond": {"$gt": ["$$wh.quantity", 0]}}
            }
        }},
        {"$addFields": {"nearby_stock": {"$sum": "$nearby_warehouses.quantity"},
                        "nearby_cities": "$nearby_warehouses.city"}},
        {"$sort": {"nearby_stock": -1, "ratings_summary.average": -1}},
        {"$limit": 10},
        {"$project": {"_id":0,"product_id":1,"name":1,"category":1,"price":1,
                       "ratings_summary.average":1,"nearby_stock":1,"nearby_cities":1}}
    ]
    results = list(db.products.aggregate(pipeline))
    print(f"\n📍 Produtos disponíveis ({RADIUS_KM}km de Luanda):")
    print(tabulate([[r["product_id"], r["name"][:28], r["category"],
                     f"Kz {r['price']:,.0f}", r["ratings_summary"]["average"],
                     r["nearby_stock"], ", ".join(r["nearby_cities"][:2])]
                    for r in results],
                   headers=["ID","Nome","Categoria","Preço (AOA)","Rating","Stock","Armazéns"],
                   tablefmt="simple"))
    return results

# ══════════════════════════════════════════════════════════════════════════════
# Q6 — Análise de Séries Temporais
# ══════════════════════════════════════════════════════════════════════════════
def query6_price_trends():
    six_months_ago = datetime.now() - timedelta(days=180)
    pipeline = [
        {"$match": {"status": "active", "category": "Eletrónicos"}},
        {"$unwind": "$price_history"},
        {"$match": {"price_history.date": {"$gte": six_months_ago}}},
        {"$group": {
            "_id": {"year": {"$year": "$price_history.date"},
                    "month": {"$month": "$price_history.date"},
                    "subcategory": "$subcategory"},
            "avg_price": {"$avg": "$price_history.price"},
            "min_price": {"$min": "$price_history.price"},
            "max_price": {"$max": "$price_history.price"},
            "changes": {"$sum": 1}
        }},
        {"$sort": {"_id.year": 1, "_id.month": 1}},
        {"$project": {
            "_id": 0,
            "period": {"$concat": [{"$toString":"$_id.year"},"-",
                        {"$cond":[{"$lt":["$_id.month",10]},
                                  {"$concat":["0",{"$toString":"$_id.month"}]},
                                  {"$toString":"$_id.month"}]}]},
            "subcategory": "$_id.subcategory",
            "avg_price": {"$round":["$avg_price",0]},
            "min_price": {"$round":["$min_price",0]},
            "max_price": {"$round":["$max_price",0]},
            "changes": 1
        }},
        {"$limit": 20}
    ]
    results = list(db.products.aggregate(pipeline))
    print("\n Evolução de Preços — Eletrónicos (6 meses) em AOA:")
    print(tabulate([[r["period"], r["subcategory"][:14],
                     f"Kz {r['avg_price']:,.0f}", f"Kz {r['min_price']:,.0f}",
                     f"Kz {r['max_price']:,.0f}", r["changes"]]
                    for r in results],
                   headers=["Período","Subcategoria","Preço Médio","Mínimo","Máximo","Mudanças"],
                   tablefmt="simple"))
    return results

# ══════════════════════════════════════════════════════════════════════════════
# Q7 — Produtos em Tendência ($lookup)
# ══════════════════════════════════════════════════════════════════════════════
def query7_trending_products():
    three_years_ago = datetime.now() - timedelta(days=3650)
    pipeline = [
        {"$match": {"created_at": {"$gte": three_years_ago}, "rating": {"$gte": 4}, "verified_purchase": True}},
        {"$group": {
            "_id": "$product_id",
            "review_count": {"$sum": 1},
            "avg_rating": {"$avg": "$rating"},
            "helpful_votes": {"$sum": "$helpful_votes"}
        }},
        {"$match": {"review_count": {"$gte": 5}}},
        {"$lookup": {
            "from": "products",
            "localField": "_id",
            "foreignField": "product_id",
            "as": "product",
            "pipeline": [
                {"$match": {"status": "active", "in_stock": True}},
                {"$project": {"name":1,"brand":1,"category":1,"price":1,"ratings_summary":1}}
            ]
        }},
        {"$unwind": "$product"},
        {"$addFields": {
            "trending_score": {"$add": [
                {"$multiply": ["$review_count", 2]},
                {"$multiply": ["$avg_rating", 10]},
                {"$divide": ["$helpful_votes", 100]}
            ]}
        }},
        {"$sort": {"trending_score": -1}},
        {"$limit": 10},
        {"$project": {
            "_id":0,
            "product_id": "$_id",
            "name": "$product.name",
            "brand": "$product.brand",
            "price": "$product.price",
            "global_rating": "$product.ratings_summary.average",
            "reviews": "$review_count",
            "recent_avg": {"$round":["$avg_rating",2]},
            "trending_score": {"$round":["$trending_score",2]}
        }}
    ]
    results = list(db.reviews.aggregate(pipeline, allowDiskUse=True))
    print("\n Produtos em Tendência:")
    print(tabulate([[r["product_id"], r["name"][:28], r["brand"],
                     f"Kz {r['price']:,.0f}", r["global_rating"],
                     r["reviews"], r["trending_score"]]
                    for r in results],
                   headers=["ID","Nome","Marca","Preço (AOA)","Rating","Reviews","Trend Score"],
                   tablefmt="simple"))
    return results

# ══════════════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════════════
def main():
    print("=" * 70)
    print("  SGBD II — Consultas Avançadas: Catálogo E-commerce MongoDB")
    print("=" * 70)
    try:
        client.admin.command('ping')
        print(" Conectado ao MongoDB!")
    except Exception as e:
        print(f" Erro: {e}")
        print(" Inicie o ambiente: docker-compose up -d")
        return
    count = db.products.estimated_document_count()
    if count == 0:
        print("  Base de dados vazia! Execute: python scripts/seed_data.py"); return
    print(f"\n Total de produtos: {count:,}")

    queries = [
        ("Q1 — Pesquisa Facetada (Filtros + Ordenação)", query1_faceted_search),
        ("Q2 — Análise de Receita por Categoria", query2_category_revenue),
        ("Q3 — Full-Text com Score Composto", query3_fulltext_search),
        ("Q4 — Atualização Parcial Complexa (Arrays)", query4_complex_update),
        ("Q5 — Geoespacial: Armazéns Próximos de Luanda", query5_geospatial),
        ("Q6 — Séries Temporais ($unwind por mês)", query6_price_trends),
        ("Q7 — Produtos em Tendência ($lookup + Score)", query7_trending_products),
    ]

    timing = []
    for name, fn in queries:
        try:
            _, elapsed = run_query(name, fn)
            timing.append((name[:55], f"{elapsed:.2f} ms"))
        except Exception as e:
            print(f" Erro: {e}")
            timing.append((name[:55], "ERRO"))

    print(f"\n{'='*70}")
    print("  SUMÁRIO DE DESEMPENHO")
    print(f"{'='*70}")
    print(tabulate(timing, headers=["Query", "Tempo"], tablefmt="grid"))
    client.close()
    print("\n Todas as queries executadas com sucesso!")

if __name__ == "__main__":
    main()
