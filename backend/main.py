# FastAPI entrypoint for Moonshot dashboard backend
from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def root():
    return {"message": "Moonshot Competitive Intelligence Dashboard API"}
