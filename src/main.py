from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from pathlib import Path

app = FastAPI()

# Set up templates directory
templates = Jinja2Templates(directory="src/templates")

@app.get("/")
def get_home_page(request: Request):
    return templates.TemplateResponse(
        "home.html",
        {"request": request}
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
