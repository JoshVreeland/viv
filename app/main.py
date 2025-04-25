from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.database import Base, engine
from app.db_init import init_db
from app.routes.auth_routes import router as auth_router
from app.routes.form_routes import router as form_router
from dotenv import load_dotenv

app = FastAPI()

load_dotenv()

# Initialize DB & create tables
init_db()
Base.metadata.create_all(bind=engine)

# Mount static assets
app.mount("/static", StaticFiles(directory="app/static"), name="static")
app.mount("/finalized_pdfs", StaticFiles(directory="finalized_pdfs"), name="finalized_pdfs")

# Include your routers
app.include_router(auth_router)    # /login, /register, /logout
app.include_router(form_router)    # /, /claim-package, /clients, /admin/dashboard, etc.
