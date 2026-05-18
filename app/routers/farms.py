import pandas as pd
from fastapi import APIRouter, Query, HTTPException
from typing import Optional

from app.database import get_engine
from app.validators import (
    validate,
    VALID_REGIONS, VALID_FARM_TYPES, VALID_SEASONS,
    VALID_YEARS, VALID_CROP_CATEGORIES, VALID_MARKET_TYPES,
    VALID_METRICS, VALID_QUALITY_GRADES,
)

router = APIRouter(prefix="/farms", tags=["Farm Performance"])


def _load_view() -> pd.DataFrame:
    """Load vw_harvest_full and add derived columns."""
    try:
        df = pd.read_sql("SELECT * FROM vw_harvest_full", get_engine())
        df["total_cost_bdt"] = df["input_cost_bdt"]
        df["post_harvest_loss_ton"] = df["quantity_lost_ton"]
        df["loss_pct"] = (
            df["quantity_lost_ton"]
            / df["quantity_harvested_ton"].replace(0, float("nan"))
            * 100
        ).round(2)
        return df
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


def _only_active(filters: dict) -> dict:
    return {k: v for k, v in filters.items() if v is not None}


# ────────────────────────────────────────────────────────────────────────────
# Endpoint 1 — Farm Summary
# GET /farms/summary
@router.get("/summary", summary="Endpoint 1: Farm Summary — revenue, profit, cost, loss per farm")
def farm_summary(
    region: Optional[str] = Query(None, description=f"Accepted: {sorted(VALID_REGIONS)}"),
    farm_type: Optional[str] = Query(None, description=f"Accepted: {sorted(VALID_FARM_TYPES)}"),
    year: Optional[int] = Query(None, description="2022 | 2023 | 2024"),
    season: Optional[str] = Query(None, description=f"Accepted: {sorted(VALID_SEASONS)}"),
):
    validate(region, VALID_REGIONS, "region")
    validate(farm_type, VALID_FARM_TYPES, "farm_type")
    validate(season, VALID_SEASONS, "season")
    if year is not None and year not in VALID_YEARS:
        raise HTTPException(status_code=422, detail=f"Invalid year '{year}'. Accepted: {sorted(VALID_YEARS)}")

    df = _load_view()

    if region:    df = df[df["region"] == region]
    if farm_type: df = df[df["farm_type"] == farm_type]
    if year:      df = df[df["year"] == year]
    if season:    df = df[df["season"] == season]

    if df.empty:
        return {
            "total_farms": 0,
            "filters_applied": _only_active({"region": region, "year": year, "farm_type": farm_type, "season": season}),
            "data": [],
        }

    grouped = (
        df.groupby(["farm_name", "region", "farm_type"])
        .agg(
            total_revenue_bdt=("revenue_bdt", "sum"),
            total_cost_bdt=("input_cost_bdt", "sum"),
            net_profit_bdt=("net_profit_bdt", "sum"),
            avg_loss_pct=("loss_pct", "mean"),
        )
        .reset_index()
    )

    grouped["avg_loss_pct"]      = grouped["avg_loss_pct"].round(2)
    grouped["total_revenue_bdt"] = grouped["total_revenue_bdt"].round(0).astype(int)
    grouped["total_cost_bdt"]    = grouped["total_cost_bdt"].round(0).astype(int)
    grouped["net_profit_bdt"]    = grouped["net_profit_bdt"].round(0).astype(int)

    data = grouped[[
        "farm_name", "region", "farm_type",
        "total_revenue_bdt", "total_cost_bdt", "net_profit_bdt", "avg_loss_pct",
    ]].to_dict(orient="records")

    return {
        "total_farms": len(data),
        "filters_applied": _only_active({"region": region, "year": year, "farm_type": farm_type, "season": season}),
        "data": data,
    }


# ────────────────────────────────────────────────────────────────────────────
# Endpoint 2 — Single Farm Performance
# GET /farms/{farm_name}/performance
@router.get("/{farm_name}/performance", summary="Endpoint 2: Single Farm — crop/year/market breakdown")
def single_farm_performance(
    farm_name: str,
    year: Optional[int] = Query(None, description="2022 | 2023 | 2024"),
    crop_category: Optional[str] = Query(None, description=f"Accepted: {sorted(VALID_CROP_CATEGORIES)}"),
    market_type: Optional[str] = Query(None, description=f"Accepted: {sorted(VALID_MARKET_TYPES)}"),
):
    validate(crop_category, VALID_CROP_CATEGORIES, "crop_category")
    validate(market_type, VALID_MARKET_TYPES, "market_type")
    if year is not None and year not in VALID_YEARS:
        raise HTTPException(status_code=422, detail=f"Invalid year '{year}'. Accepted: {sorted(VALID_YEARS)}")

    df = _load_view()

    farm_rows = df[df["farm_name"].str.lower() == farm_name.lower()]
    if farm_rows.empty:
        raise HTTPException(status_code=404, detail=f"Farm '{farm_name}' not found.")

    info = farm_rows.iloc[0]

    filtered = farm_rows.copy()
    if year:          filtered = filtered[filtered["year"] == year]
    if crop_category: filtered = filtered[filtered["crop_category"] == crop_category]
    if market_type:   filtered = filtered[filtered["market_type"] == market_type]

    if filtered.empty:
        performance = []
    else:
        perf = (
            filtered.groupby(["crop_name", "year", "market_type", "quality_grade"])
            .agg(
                quantity_sold_ton=("quantity_sold_ton", "sum"),
                revenue_bdt=("revenue_bdt", "sum"),
                net_profit_bdt=("net_profit_bdt", "sum"),
            )
            .reset_index()
        )
        perf["quantity_sold_ton"] = perf["quantity_sold_ton"].round(1)
        perf["revenue_bdt"]       = perf["revenue_bdt"].round(0).astype(int)
        perf["net_profit_bdt"]    = perf["net_profit_bdt"].round(0).astype(int)
        performance = perf.to_dict(orient="records")

    return {
        "farm_name": info["farm_name"],
        "owner": info["owner_name"],
        "region": info["region"],
        "farm_type": info["farm_type"],
        "filters_applied": _only_active({"year": year, "crop_category": crop_category, "market_type": market_type}),
        "performance": performance,
    }


# ────────────────────────────────────────────────────────────────────────────
# Endpoint 3 — Top Farms Ranking
@router.get("/top", summary="Endpoint 3: Top N farms ranked by profit / revenue / yield")
def top_farms(
    metric: str = Query("profit", description="profit | revenue | yield"),
    region: Optional[str] = Query(None, description=f"Accepted: {sorted(VALID_REGIONS)}"),
    farm_type: Optional[str] = Query(None, description=f"Accepted: {sorted(VALID_FARM_TYPES)}"),
    year: Optional[int] = Query(None, description="2022 | 2023 | 2024"),
    limit: int = Query(10, ge=1, description="Default 10"),
):
    validate(metric, VALID_METRICS, "metric")
    validate(region, VALID_REGIONS, "region")
    validate(farm_type, VALID_FARM_TYPES, "farm_type")
    if year is not None and year not in VALID_YEARS:
        raise HTTPException(status_code=422, detail=f"Invalid year '{year}'. Accepted: {sorted(VALID_YEARS)}")

    df = _load_view()

    if region:    df = df[df["region"] == region]
    if farm_type: df = df[df["farm_type"] == farm_type]
    if year:      df = df[df["year"] == year]

    if df.empty:
        return {
            "metric": metric,
            "filters_applied": _only_active({"region": region, "farm_type": farm_type, "year": year, "limit": limit}),
            "rankings": [],
        }

    grouped = (
        df.groupby(["farm_name", "region", "farm_type"])
        .agg(
            net_profit_bdt=("net_profit_bdt", "sum"),
            total_revenue_bdt=("revenue_bdt", "sum"),
            total_yield_ton=("quantity_harvested_ton", "sum"),
            total_area_ha=("area_planted_ha", "sum"),
        )
        .reset_index()
    )

    grouped["yield_efficiency"] = (
        grouped["total_yield_ton"] / grouped["total_area_ha"].replace(0, float("nan"))
    ).round(3)

    sort_col = {"profit": "net_profit_bdt", "revenue": "total_revenue_bdt", "yield": "yield_efficiency"}[metric]
    ranked = grouped.sort_values(sort_col, ascending=False).head(limit).reset_index(drop=True)
    ranked["rank"] = ranked.index + 1
    ranked["net_profit_bdt"]    = ranked["net_profit_bdt"].round(0).astype(int)
    ranked["total_revenue_bdt"] = ranked["total_revenue_bdt"].round(0).astype(int)

    rankings = []
    for _, row in ranked.iterrows():
        entry = {
            "rank": int(row["rank"]),
            "farm_name": row["farm_name"],
            "region": row["region"],
            "farm_type": row["farm_type"],
            "net_profit_bdt": int(row["net_profit_bdt"]),
            "total_revenue_bdt": int(row["total_revenue_bdt"]),
        }
        if metric == "yield":
            entry["yield_efficiency_ton_per_ha"] = float(row["yield_efficiency"])
        rankings.append(entry)

    return {
        "metric": metric,
        "filters_applied": _only_active({"region": region, "farm_type": farm_type, "year": year, "limit": limit}),
        "rankings": rankings,
    }

# Endpoint 4 — Loss Analysis
# GET /farms/loss-analysis
@router.get("/loss-analysis", summary="Endpoint 4: Post-harvest loss data by region, season, crop, quality")
def loss_analysis(
    region: Optional[str] = Query(None, description=f"Accepted: {sorted(VALID_REGIONS)}"),
    year: Optional[int] = Query(None, description="2022 | 2023 | 2024"),
    season: Optional[str] = Query(None, description=f"Accepted: {sorted(VALID_SEASONS)}"),
    quality_grade: Optional[str] = Query(None, description="A | B | C | D"),
    crop_category: Optional[str] = Query(None, description=f"Accepted: {sorted(VALID_CROP_CATEGORIES)}"),
):
    validate(region, VALID_REGIONS, "region")
    validate(season, VALID_SEASONS, "season")
    validate(quality_grade, VALID_QUALITY_GRADES, "quality_grade")
    validate(crop_category, VALID_CROP_CATEGORIES, "crop_category")
    if year is not None and year not in VALID_YEARS:
        raise HTTPException(status_code=422, detail=f"Invalid year '{year}'. Accepted: {sorted(VALID_YEARS)}")

    df = _load_view()

    if region:        df = df[df["region"] == region]
    if year:          df = df[df["year"] == year]
    if season:        df = df[df["season"] == season]
    if quality_grade: df = df[df["quality_grade"] == quality_grade]
    if crop_category: df = df[df["crop_category"] == crop_category]

    if df.empty:
        return {
            "filters_applied": _only_active({"region": region, "year": year, "season": season, "quality_grade": quality_grade, "crop_category": crop_category}),
            "summary": {"total_harvested_ton": 0, "total_lost_ton": 0, "overall_loss_pct": 0},
            "breakdown": [],
        }

    total_harvested  = df["quantity_harvested_ton"].sum()
    total_lost       = df["quantity_lost_ton"].sum()
    overall_loss_pct = round(total_lost / total_harvested * 100, 2) if total_harvested > 0 else 0

    grouped = (
        df.groupby(["region", "crop_category", "quality_grade", "pesticide_residue"])
        .agg(
            total_harvested_ton=("quantity_harvested_ton", "sum"),
            total_lost_ton=("quantity_lost_ton", "sum"),
        )
        .reset_index()
    )

    grouped["loss_pct"] = (
        grouped["total_lost_ton"] / grouped["total_harvested_ton"].replace(0, float("nan")) * 100
    ).round(2)
    grouped["total_lost_ton"] = grouped["total_lost_ton"].round(2)

    breakdown = grouped[[
        "region", "crop_category", "quality_grade",
        "total_lost_ton", "loss_pct", "pesticide_residue",
    ]].to_dict(orient="records")

    return {
        "filters_applied": _only_active({"region": region, "year": year, "season": season, "quality_grade": quality_grade, "crop_category": crop_category}),
        "summary": {
            "total_harvested_ton": round(float(total_harvested), 2),
            "total_lost_ton": round(float(total_lost), 2),
            "overall_loss_pct": overall_loss_pct,
        },
        "breakdown": breakdown,
    }