# Agriculture DB — FastAPI Assessment

A REST API built with **FastAPI + pandas + SQLAlchemy** that exposes 8 analytical endpoints over the `agriculture_db` MySQL database.
Addtionally add a Dashboard to view the analytics.
Note: Kindly ensure that all validation inputs are entered with proper case sensitivity.
---

## Project Structure

```
agriculture_api/
├── app/
│   ├── __init__.py
│   ├── main.py          # FastAPI app entry-point
│   ├── database.py      # SQLAlchemy engine + connection helper
│   ├── validators.py    # Accepted filter values & validation helper
│   └── routers/
│       ├── __init__.py
│       ├── farms.py          # Endpoints 1-4  (Farm Performance Report)
│       └── crops_markets.py  # Endpoints 5-8  (Crop & Market Intelligence)
├── run.py               # Convenience launcher (uvicorn with --reload)
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
├── .env.example
└── README.md
```

## Setup & Run

### 1. Clone & enter the project

```bash
git clone <your-repo-url>
cd agriculture_api
```

### 2. Configure environment variables

```bash
cp .env.example .env
# Edit .env with the DB credentials that are provided
```

`.env` contents:
```
DB_HOST=<host>
DB_PORT=3306
DB_USER=<username>
DB_PASSWORD=<password>
DB_NAME=agriculture_db
```

### 3a. Run locally (without Docker)

```bash
python -m venv venv
source venv/bin/activate        
pip install -r requirements.txt
python run.py
```

API is now live at **http://localhost:8000**  
Interactive docs at **http://localhost:8000/docs**

### 3b. Run with Docker

```bash
docker build -t agriculture-api .
docker run --env-file .env -p 5000:8000 agriculture-api
```

### 3c. Run with Docker Compose

```bash
docker compose up --build
```

---

## API Endpoints

### Report 1 — Farm Performance

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/farms/summary` | All farms: revenue, profit, cost, avg loss |
| GET | `/farms/{farm_id}/performance` | Single farm breakdown by crop/year/market |
| GET | `/farms/top` | Top N farms ranked by profit / revenue / yield |
| GET | `/farms/loss-analysis` | Post-harvest loss by region, season, crop, quality |

### Report 2 — Crop & Market Intelligence

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/crops/yield-efficiency` | Actual yield vs national benchmark |
| GET | `/crops/seasonal-trend` | Revenue & quantity trends across seasons |
| GET | `/markets/price-comparison` | Average prices by market type / district |
| GET | `/crops/quality-breakdown` | Grade distribution + pesticide residue |

---

## Filter Reference

All filter parameters with accepted values:

| Parameter | Accepted Values |
|-----------|----------------|
| `region` | Dhaka, Chittagong, Sylhet, Rajshahi, Khulna, Rangpur, Barisal, Mymensingh |
| `farm_type` | Small, Medium, Large, Commercial |
| `crop_category` | Cereal, Vegetable, Fruit, Pulse, Oilseed, Cash Crop, Spice |
| `season` | Spring, Summer, Autumn, Winter |
| `market_type` | Local, Wholesale, Export, Retail, Government Procurement |
| `price_tier` | Low, Medium, High, Premium |
| `quality_grade` | A, B, C, D |
| `pesticide_residue` | None, Trace, Low, High |
| `water_requirement` | Low, Medium, High |
| `year` | 2022, 2023, 2024 |
| `quarter` | 1, 2, 3, 4 |
| `metric` | profit, revenue, yield |
| `limit` | Any positive integer (default: 10) |

Passing an invalid value returns **HTTP 422** with a clear error message listing accepted values.

---

## Evaluation Areas

| Area | Weight |
|------|--------|
| Database Connection (SQLAlchemy, env-based credentials) | 15% |
| pandas Processing (aggregations, filtering) | 30% |
| FastAPI Endpoints (all 8 working, correct JSON shape) | 30% |
| Code Quality (readable, no duplicate logic) | 15% |
| Error Handling (HTTP 422 for invalid filters) | 10% |
| Docker (bonus) | +10% |

---

## Tech Stack

- **Python 3.11**
- **FastAPI 0.111** + **Uvicorn**
- **SQLAlchemy 2.0** + **PyMySQL**
- **pandas 2.2**
- **python-dotenv**
