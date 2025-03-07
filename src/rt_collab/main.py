from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from rt_collab.api.routes import router as api_router

app = FastAPI(title="rt-collab")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"] ,
    allow_headers=["*"],
)

app.include_router(api_router)


@app.get("/healthz")
async def healthz():
    return {"status": "ok"}


@app.get("/readyz")
async def readyz():
    return {"status": "ready"}
