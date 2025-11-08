import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional

from database import create_document, get_documents, db

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def read_root():
    return {"message": "Hello from FastAPI Backend!"}


@app.get("/api/hello")
def hello():
    return {"message": "Hello from the backend API!"}


class WaitlistIn(BaseModel):
    address: str = Field(..., description="Solana wallet address (base58)")
    source: Optional[str] = Field(None, description="where user clicked join")


@app.post("/api/waitlist")
def join_waitlist(payload: WaitlistIn):
    addr = (payload.address or "").strip()
    if len(addr) < 32 or len(addr) > 60:
        raise HTTPException(status_code=400, detail="Invalid wallet address")
    try:
        _id = create_document("waitlist", {"address": addr, "source": payload.source or "unknown"})
        return {"ok": True, "id": _id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/waitlist")
def list_waitlist(limit: int = 200):
    try:
        docs = get_documents("waitlist", {}, limit=limit)
        out = [
            {
                "id": str(d.get("_id")),
                "address": d.get("address"),
                "source": d.get("source"),
                "created_at": d.get("created_at"),
            }
            for d in docs
        ]
        # newest first when created_at exists
        out.sort(key=lambda x: x.get("created_at") or 0, reverse=True)
        return {"ok": True, "items": out}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/test")
def test_database():
    """Test endpoint to check if database is available and accessible"""
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": []
    }

    try:
        if db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Configured"
            response["database_name"] = db.name if hasattr(db, 'name') else "✅ Connected"
            response["connection_status"] = "Connected"
            try:
                collections = db.list_collection_names()
                response["collections"] = collections[:10]
                response["database"] = "✅ Connected & Working"
            except Exception as e:
                response["database"] = f"⚠️  Connected but Error: {str(e)[:50]}"
        else:
            response["database"] = "⚠️  Available but not initialized"

    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:50]}"

    response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
    response["database_name"] = "✅ Set" if os.getenv("DATABASE_NAME") else "❌ Not Set"

    return response


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
