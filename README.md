#  Catálogo de Produtos E-commerce — NoSQL com MongoDB
## Trabalho Prático SGBD II — 2025/2026

**Subdomínio:** Catálogo de Produtos Dinâmico  
**Tecnologia:** MongoDB 7.0 — Replica Set 3 nós (Docker)  
**Docente:** Moyo Kanivengidio  

---

## Pré-requisitos

| Ferramenta | Versão Mínima | Download |
|---|---|---|
| Docker Desktop | 24.x | https://www.docker.com/products/docker-desktop |
| Python | 3.9+ | https://www.python.org/downloads/ |

>  **Windows:** Durante a instalação do Python marcar obrigatoriamente **"Add Python to PATH"**

---

## Instalação e Execução (Passo a Passo)

### 1. Clonar o repositório
```bash
git clone https://github.com/Samuel913-ia/sgbd2-nosql-ecommerce.git
cd sgbd2-nosql-ecommerce
```

### 2. Instalar bibliotecas Python
```bash
pip install pymongo faker tqdm tabulate
```

### 3. Iniciar o cluster MongoDB (3 nós)
```bash
docker-compose up -d
```
Aguardar 20 segundos para o Replica Set inicializar.

### 4. Verificar os containers
```bash
docker-compose ps
```
Devem aparecer 4 containers com estado **Up**: mongo1, mongo2, mongo3, mongo-express.

### 5. Inicializar o Replica Set (apenas na primeira vez)
```bash
docker exec -it mongo1 mongosh --eval "rs.initiate({_id:'rs0',members:[{_id:0,host:'mongo1:27017',priority:2},{_id:1,host:'mongo2:27017',priority:1},{_id:2,host:'mongo3:27017',priority:1}]})"
```

### 6. Adicionar nomes ao ficheiro hosts (Windows)
Abrir CMD como **Administrador** e correr:
```bash
docker inspect mongo1 --format "{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}"
docker inspect mongo2 --format "{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}"
docker inspect mongo3 --format "{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}"
```
Depois adicionar ao ficheiro `C:\Windows\System32\drivers\etc\hosts`:
```
IP_MONGO1 mongo1
IP_MONGO2 mongo2
IP_MONGO3 mongo3
```
> **Mac/Linux:** Não precisa deste passo — a resolução de nomes Docker funciona automaticamente.

### 7. Inserir os dados (310.000 documentos)
```bash
py scripts/seed_data.py        # Windows
python3 scripts/seed_data.py   # Mac/Linux
```
Tempo estimado: 5–10 minutos

### 8. Executar as 7 consultas avançadas
```bash
py queries/advanced_queries.py        # Windows
python3 queries/advanced_queries.py   # Mac/Linux
```

### 9. Interface web (opcional)
Abrir o browser em: **http://localhost:8081**  
Utilizador: `admin` | Password: `admin123`

---

## Estrutura do Projeto

```
sgbd2-nosql-ecommerce/
├── docker-compose.yml          # Cluster MongoDB 3 nós + Mongo Express
├── README.md                   # Este ficheiro
├── scripts/
│   └── seed_data.py            # Gera e insere 310.000+ documentos
├── queries/
│   └── advanced_queries.py     # 7 consultas avançadas com resultados
└── docs/
    └── relatorio_final_AOA.pdf # Relatório técnico completo
```

---

##  Resumo das Consultas

| Query | Descrição | Tempo Real |
|---|---|---|
| Q1 | Pesquisa Facetada ($facet) | 113 ms |
| Q2 | Análise Receita por Categoria ($group) | 985 ms |
| Q3 | Full-Text com Score Composto ($text) | 91 ms |
| Q4 | Atualização Parcial Arrays ($push, $addToSet) | 280 ms |
| Q5 | Geoespacial — Armazéns 100km Lisboa | 1.309 ms |
| Q6 | Séries Temporais ($unwind por mês) | 465 ms |
| Q7 | Tendências ($lookup + Score composto) | 81.118 ms |

---

## Parar o ambiente
```bash
docker-compose down
```
> Os dados ficam guardados nos volumes Docker. Para retomar basta `docker-compose up -d`.

---

