import os
import pandas as pd
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv(override=True)  # Load environment variables from .env file, override existing ones

HOST = os.getenv("HOST")
PORT = os.getenv("PORT")
USER = os.getenv("USER")
PASSWORD = os.getenv("PASSWORD")
DB = os.getenv("DB", "agriculture_db")

DATABASE_URL = f"mysql+pymysql://{USER}:{PASSWORD}@{HOST}:{PORT}/{DB}"

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=3600,
)


def get_engine():
    return engine


def load_full_harvest_dataframe() -> pd.DataFrame:
    """Load the full harvest star schema join, including derived columns required by the API."""
    sql = text(
        "SELECT f.harvest_id, f.farm_id, farm.farm_name, farm.owner_name, farm.region, "
        "farm.district AS farm_district, farm.farm_type, farm.total_area_ha, c.crop_id, c.crop_name, "
        "c.crop_category, c.growing_season, c.avg_yield_ton_per_ha AS benchmark_yield_ton_per_ha, "
        "c.water_requirement, d.full_date, d.month_name, d.quarter, d.year, d.season, "
        "m.market_name, m.market_type, m.price_tier, m.district AS market_district, "
        "f.area_planted_ha, f.quantity_harvested_ton, f.quantity_sold_ton, f.quantity_lost_ton AS post_harvest_loss_ton, "
        "f.price_per_ton_bdt, f.revenue_bdt, f.input_cost_bdt AS total_cost_bdt, f.net_profit_bdt, "
        "f.quality_grade, f.moisture_pct, f.pesticide_residue "
        "FROM fact_harvest_sales AS f "
        "JOIN dim_farm AS farm ON f.farm_id = farm.farm_id "
        "JOIN dim_crop AS c ON f.crop_id = c.crop_id "
        "JOIN dim_date AS d ON f.date_id = d.date_id "
        "JOIN dim_market AS m ON f.market_id = m.market_id"
    )
    return pd.read_sql(sql, engine)


def test_connection():
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception as e:
        print(f"Database connection failed: {e}")
        return False
