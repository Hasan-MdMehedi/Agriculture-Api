import pandas as pd
from fastapi import APIRouter, Query, HTTPException
from typing import Optional

from app.database import load_full_harvest_dataframe
from app.validators import (
    validate,
    VALID_REGIONS, VALID_SEASONS, VALID_YEARS,
    VALID_CROP_CATEGORIES, VALID_MARKET_TYPES,
    VALID_QUALITY_GRADES, VALID_PESTICIDE_RESIDUES,
    VALID_PRICE_TIERS, VALID_WATER_REQUIREMENTS,
    VALID_QUARTERS,
)

router = APIRouter(tags=["Crop & Market Intelligence"])

def _load_view(view_name: str) -> pd.DataFrame:
    try:
        if view_name == "vw_harvest_full":
            return load_full_harvest_dataframe()
        return pd.DataFrame()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


def _only_active(filters: dict) -> dict:
    return {k: v for k, v in filters.items() if v is not None}


@router.get("/crops/yield-efficiency", summary="Endpoint 5: Actual yield vs national benchmark per crop")
def crop_yield_efficiency(
    crop_category: Optional[str] = Query(None, description=f"Filter by crop category. Accepted: {sorted(VALID_CROP_CATEGORIES)}"),
    season: Optional[str] = Query(None, description=f"Filter by season. Accepted: {sorted(VALID_SEASONS)}"),
    year: Optional[int] = Query(None, description="Filter by year (2022, 2023, 2024)"),
    region: Optional[str] = Query(None, description=f"Filter by region. Accepted: {sorted(VALID_REGIONS)}"),
    water_requirement: Optional[str] = Query(None, description="Filter by water requirement: Low | Medium | High"),
):
    validate(crop_category, VALID_CROP_CATEGORIES, "crop_category")
    validate(season, VALID_SEASONS, "season")
    validate(region, VALID_REGIONS, "region")
    validate(water_requirement, VALID_WATER_REQUIREMENTS, "water_requirement")
    if year is not None and year not in VALID_YEARS:
        raise HTTPException(status_code=422, detail=f"Invalid year '{year}'. Accepted: {sorted(VALID_YEARS)}")

    df = _load_view("vw_harvest_full")

    if crop_category:
        df = df[df["crop_category"] == crop_category]
    if season:
        df = df[df["season"] == season]
    if year:
        df = df[df["year"] == year]
    if region:
        df = df[df["region"] == region]
    if water_requirement:
        df = df[df["water_requirement"] == water_requirement]

    if df.empty:
        return {"filters_applied": _only_active({"crop_category": crop_category, "season": season, "year": year, "region": region, "water_requirement": water_requirement}), "data": []}

    # Aggregate per crop + season
    grouped = (
        df.groupby(["crop_name", "crop_category", "season", "growing_season"])
        .agg(
            avg_yield_benchmark_ton_per_ha=("benchmark_yield_ton_per_ha", "mean"),
            actual_total_yield_ton=("quantity_harvested_ton", "sum"),
            total_area_planted_ha=("area_planted_ha", "sum"),
        )
        .reset_index()
    )

    grouped["actual_avg_yield_ton_per_ha"] = (
        grouped["actual_total_yield_ton"] / grouped["total_area_planted_ha"].replace(0, float("nan"))
    ).round(2)

    grouped["efficiency_pct"] = (
        grouped["actual_avg_yield_ton_per_ha"] / grouped["avg_yield_benchmark_ton_per_ha"].replace(0, float("nan")) * 100
    ).round(2)

    grouped["avg_yield_benchmark_ton_per_ha"] = grouped["avg_yield_benchmark_ton_per_ha"].round(2)
    grouped["total_area_planted_ha"] = grouped["total_area_planted_ha"].round(2)

    data = grouped[[
        "crop_name", "crop_category",
        "avg_yield_benchmark_ton_per_ha", "actual_avg_yield_ton_per_ha",
        "efficiency_pct", "total_area_planted_ha", "season",
    ]].to_dict(orient="records")

    return {
        "filters_applied": _only_active({"crop_category": crop_category, "season": season, "year": year, "region": region, "water_requirement": water_requirement}),
        "data": data,
    }


# Endpoint 6 — Seasonal Revenue Trend
@router.get("/crops/seasonal-trend", summary=" Endpoint 6: Revenue & quantity trend across seasons and years")
def seasonal_revenue_trend(
    crop_name: Optional[str] = Query(None, description="Filter by exact crop name"),
    crop_category: Optional[str] = Query(None, description=f"Filter by crop category. Accepted: {sorted(VALID_CROP_CATEGORIES)}"),
    year: Optional[int] = Query(None, description="Filter by year (2022, 2023, 2024)"),
    quarter: Optional[int] = Query(None, description="Filter by quarter: 1 | 2 | 3 | 4"),
    market_type: Optional[str] = Query(None, description=f"Filter by market type. Accepted: {sorted(VALID_MARKET_TYPES)}"),
):
    validate(crop_category, VALID_CROP_CATEGORIES, "crop_category")
    validate(market_type, VALID_MARKET_TYPES, "market_type")
    if year is not None and year not in VALID_YEARS:
        raise HTTPException(status_code=422, detail=f"Invalid year '{year}'. Accepted: {sorted(VALID_YEARS)}")
    if quarter is not None and quarter not in VALID_QUARTERS:
        raise HTTPException(status_code=422, detail=f"Invalid quarter '{quarter}'. Accepted: 1, 2, 3, 4")

    df = _load_view("vw_harvest_full")

    if crop_name:
        df = df[df["crop_name"].str.lower() == crop_name.lower()]
    if crop_category:
        df = df[df["crop_category"] == crop_category]
    if year:
        df = df[df["year"] == year]
    if quarter:
        df = df[df["quarter"] == quarter]
    if market_type:
        df = df[df["market_type"] == market_type]

    if df.empty:
        return {"filters_applied": _only_active({"crop_name": crop_name, "crop_category": crop_category, "year": year, "quarter": quarter, "market_type": market_type}), "trend": []}

    grouped = (
        df.groupby(["crop_name", "year", "quarter", "season"])
        .agg(
            total_quantity_sold_ton=("quantity_sold_ton", "sum"),
            total_revenue_bdt=("revenue_bdt", "sum"),
            avg_price_per_ton_bdt=("price_per_ton_bdt", "mean"),
            num_harvests=("harvest_id", "count"),
        )
        .reset_index()
    )

    grouped["total_quantity_sold_ton"] = grouped["total_quantity_sold_ton"].round(2)
    grouped["total_revenue_bdt"] = grouped["total_revenue_bdt"].round(0).astype(int)
    grouped["avg_price_per_ton_bdt"] = grouped["avg_price_per_ton_bdt"].round(0).astype(int)
    grouped["num_harvests"] = grouped["num_harvests"].astype(int)

    trend = grouped[[
        "crop_name", "year", "quarter", "season",
        "total_quantity_sold_ton", "total_revenue_bdt",
        "avg_price_per_ton_bdt", "num_harvests",
    ]].sort_values(["year", "quarter", "crop_name"]).to_dict(orient="records")

    return {
        "filters_applied": _only_active({"crop_name": crop_name, "crop_category": crop_category, "year": year, "quarter": quarter, "market_type": market_type}),
        "trend": trend,
    }


# Endpoint 7 — Market Price Comparison

@router.get("/markets/price-comparison", summary=" Endpoint 7: Average prices by market type, district and price tier")
def market_price_comparison(
    market_type: Optional[str] = Query(None, description=f"Filter by market type. Accepted: {sorted(VALID_MARKET_TYPES)}"),
    crop_category: Optional[str] = Query(None, description=f"Filter by crop category. Accepted: {sorted(VALID_CROP_CATEGORIES)}"),
    year: Optional[int] = Query(None, description="Filter by year (2022, 2023, 2024)"),
    season: Optional[str] = Query(None, description=f"Filter by season. Accepted: {sorted(VALID_SEASONS)}"),
    price_tier: Optional[str] = Query(None, description="Filter by price tier: Low | Medium | High | Premium"),
    district: Optional[str] = Query(None, description="Filter by district name"),
):
    validate(market_type, VALID_MARKET_TYPES, "market_type")
    validate(crop_category, VALID_CROP_CATEGORIES, "crop_category")
    validate(season, VALID_SEASONS, "season")
    validate(price_tier, VALID_PRICE_TIERS, "price_tier")
    if year is not None and year not in VALID_YEARS:
        raise HTTPException(status_code=422, detail=f"Invalid year '{year}'. Accepted: {sorted(VALID_YEARS)}")

    df = _load_view("vw_harvest_full")

    if market_type:
        df = df[df["market_type"] == market_type]
    if crop_category:
        df = df[df["crop_category"] == crop_category]
    if year:
        df = df[df["year"] == year]
    if season:
        df = df[df["season"] == season]
    if price_tier:
        df = df[df["price_tier"] == price_tier]
    if district:
        df = df[df["market_district"].str.lower() == district.lower()]

    if df.empty:
        return {"filters_applied": _only_active({"market_type": market_type, "crop_category": crop_category, "year": year, "season": season, "price_tier": price_tier, "district": district}), "comparison": []}

    grouped = (
        df.groupby(["market_name", "market_type", "price_tier", "market_district", "crop_name"])
        .agg(
            avg_price_per_ton_bdt=("price_per_ton_bdt", "mean"),
            total_quantity_sold_ton=("quantity_sold_ton", "sum"),
            total_revenue_bdt=("revenue_bdt", "sum"),
        )
        .reset_index()
    )

    grouped = grouped.rename(columns={"market_district": "district"})
    grouped["avg_price_per_ton_bdt"] = grouped["avg_price_per_ton_bdt"].round(0).astype(int)
    grouped["total_quantity_sold_ton"] = grouped["total_quantity_sold_ton"].round(2)
    grouped["total_revenue_bdt"] = grouped["total_revenue_bdt"].round(0).astype(int)

    comparison = grouped[[
        "market_name", "market_type", "price_tier", "district",
        "crop_name", "avg_price_per_ton_bdt",
        "total_quantity_sold_ton", "total_revenue_bdt",
    ]].to_dict(orient="records")

    return {
        "filters_applied": _only_active({"market_type": market_type, "crop_category": crop_category, "year": year, "season": season, "price_tier": price_tier, "district": district}),
        "comparison": comparison,
    }

# Endpoint 8 — Quality Grade Breakdown
@router.get("/crops/quality-breakdown", summary=" Endpoint 8: Quality grade distribution with pesticide residue data")
def quality_grade_breakdown(
    crop_id: Optional[int] = Query(None, description="Filter by crop ID (integer)"),
    crop_category: Optional[str] = Query(None, description=f"Filter by crop category. Accepted: {sorted(VALID_CROP_CATEGORIES)}"),
    year: Optional[int] = Query(None, description="Filter by year (2022, 2023, 2024)"),
    region: Optional[str] = Query(None, description=f"Filter by region. Accepted: {sorted(VALID_REGIONS)}"),
    market_type: Optional[str] = Query(None, description=f"Filter by market type. Accepted: {sorted(VALID_MARKET_TYPES)}"),
    pesticide_residue: Optional[str] = Query(None, description="Filter by pesticide residue: None | Trace | Low | High"),
):
    validate(crop_category, VALID_CROP_CATEGORIES, "crop_category")
    validate(region, VALID_REGIONS, "region")
    validate(market_type, VALID_MARKET_TYPES, "market_type")
    validate(pesticide_residue, VALID_PESTICIDE_RESIDUES, "pesticide_residue")
    if year is not None and year not in VALID_YEARS:
        raise HTTPException(status_code=422, detail=f"Invalid year '{year}'. Accepted: {sorted(VALID_YEARS)}")

    df = _load_view("vw_harvest_full")

    if crop_id is not None:
        df = df[df["crop_id"] == crop_id]
    if crop_category:
        df = df[df["crop_category"] == crop_category]
    if year:
        df = df[df["year"] == year]
    if region:
        df = df[df["region"] == region]
    if market_type:
        df = df[df["market_type"] == market_type]
    if pesticide_residue:
        df = df[df["pesticide_residue"] == pesticide_residue]

    if df.empty:
        return {
            "filters_applied": _only_active({"crop_id": crop_id, "crop_category": crop_category, "year": year, "region": region, "market_type": market_type, "pesticide_residue": pesticide_residue}),
            "total_records": 0,
            "grade_distribution": {},
            "pesticide_residue_breakdown": {},
        }

    total = len(df)

    # Grade distribution
    grade_distribution = {}
    for grade in ["A", "B", "C", "D"]:
        grade_df = df[df["quality_grade"] == grade]
        count = len(grade_df)
        avg_revenue = int(grade_df["revenue_bdt"].mean()) if count > 0 else 0
        grade_distribution[grade] = {
            "count": count,
            "pct": round(count / total * 100, 1),
            "avg_revenue_bdt": avg_revenue,
        }

    # Pesticide residue distribution
    pesticide_residue_breakdown = {}
    for residue in ["None", "Trace", "Low", "High"]:
        r_df = df[df["pesticide_residue"] == residue]
        count = len(r_df)
        pesticide_residue_breakdown[residue] = {
            "count": count,
            "pct": round(count / total * 100, 1),
        }

    return {
        "filters_applied": _only_active({"crop_id": crop_id, "crop_category": crop_category, "year": year, "region": region, "market_type": market_type, "pesticide_residue": pesticide_residue}),
        "total_records": total,
        "grade_distribution": grade_distribution,
        "pesticide_residue_breakdown": pesticide_residue_breakdown,
    }
