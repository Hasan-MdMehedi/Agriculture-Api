import os
import pandas as pd
from fastapi import FastAPI
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from app.routers import farms, crops_markets
from app.database import test_connection, get_engine

app = FastAPI(
    title="Agriculture DB API",
    description=(
        "Agricultural data analytics API for Bangladesh.\n\n"
        "**Built with:** FastAPI · pandas · SQLAlchemy · MySQL\n\n"
        "---\n\n"
        "** Additional: To See the Dashboard, Please Visit:** [/ Dashboard_UI](/ui)\n\n"
        "**Report 1 — Farm Performance:** `farms_summary` · `farms_performance` · `farms_top` · `farms_loss_analysis`\n\n"
        "**Report 2 — Crop & Market Intelligence:** `crops_yield_efficiency` · `crops_seasonal_trend` · `markets_price_comparison` · `crops_quality_breakdown`\n\n"
        "---\n\n"
        "> Invalid filter values return **HTTP 422** with accepted options. Supported years: 2022, 2023, 2024."
    ),
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static files
STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# Routers
app.include_router(farms.router)
app.include_router(crops_markets.router)


# UI Dashboard 
@app.get("/ui", include_in_schema=False)
def dashboard():
    return FileResponse(os.path.join(STATIC_DIR, "index.html")) 


# Health / root
@app.get("/", tags=["Health"])
def root():
    db_ok = test_connection()
    return {
        "status": "ok" if db_ok else "degraded",
        "database": "connected" if db_ok else "unreachable",
        "message": "Visit /ui for the dashboard or /docs for API documentation.",
    }


@app.get("/health", tags=["Health"])
def health():
    return {"status": "ok"}


@app.get("/debug/columns", tags=["Health"])
def debug_columns():
    df = pd.read_sql("SELECT * FROM vw_harvest_full LIMIT 1", get_engine())
    return {"columns": list(df.columns), "sample": df.to_dict(orient="records")}


# Global error handler
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    return JSONResponse(
        status_code=500,
        content={"detail": f"Internal server error: {str(exc)}"},
    )