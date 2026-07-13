from fastapi import FastAPI

app = FastAPI(title="AI Infrastructure Memory")

@app.get("/")
def root():
    return {"message": "AI Infrastructure Memory API"}
