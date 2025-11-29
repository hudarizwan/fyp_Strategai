from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.scraper import router as scraper_router
# from app.api.nlp import router as nlp_router
# from app.api.analytics import router as analytics_router

# -------------------------------
#   StrategAI FastAPI App
# -------------------------------
app = FastAPI(
    title="StrategAI Backend",
    description="AI-based E-Commerce Profit Optimization System",
    version="1.0.0",
)

# -------------------------------
#   CORS (Render + Development)
# -------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],      # change later for deployment
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True,
)

# -------------------------------
#   Health Check
# -------------------------------
@app.get("/health")
def health():
    return {"status": "ok", "service": "StrategAI Backend"}

# -------------------------------
#   Attach Routers
# -------------------------------
app.include_router(scraper_router, prefix="/scraper", tags=["Scraper Agent"])

# Will add later:
# app.include_router(nlp_router, prefix="/nlp", tags=["NLP Agent"])
# app.include_router(analytics_router, prefix="/analytics", tags=["Analytics Agent"])
