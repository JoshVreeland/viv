from fastapi import (
    APIRouter, Request, Form, Depends, status, Query
)
from fastapi.responses import (
    HTMLResponse, FileResponse, RedirectResponse
)
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional
from uuid import uuid4
from datetime import datetime
import os
from app.utils.s3_helper import upload_to_s3
from app.database import get_db
from app.dependencies import require_admin
from app.models.user_model import User     
from app.models.user_model import User
from app.models.file_model import FileRecord
from app.models.client_addition import ClientAddition
from app.utils.pdf_generator import generate_pdf
from app.utils.excel_generator import generate_excel
from uuid import uuid4

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


@router.get("/", response_class=HTMLResponse)
async def login(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})


@router.get("/claim-package", response_class=HTMLResponse)
async def claim_package(request: Request):
    return templates.TemplateResponse("claim_package.html", {"request": request})


@router.post("/contents-estimate", response_class=HTMLResponse)
async def contents_estimate_post(
    request: Request,
    claim_text: str = Form(...)
):
    return templates.TemplateResponse(
        "contents_estimate.html",
        {"request": request, "claim_text": claim_text}
    )


@router.post("/finalize")
async def finalize_form(
    claimant: str = Form(...),
    property_name: str = Form(..., alias="property"),
    estimator: str = Form(...),
    estimate_type: str = Form(...),
    date_entered: str = Form(...),
    date_completed: str = Form(...),
    category: Optional[List[str]] = Form([]),
    justification: Optional[List[str]] = Form([]),
    total: Optional[List[str]] = Form([]),
    client_name: str = Form(...),
    claim_text: str = Form(...),
    db: Session = Depends(get_db),
    user: User = Depends(require_admin)
):
    # 1) Build the table rows
    rows = []
    for cat, just, tot in zip(category, justification, total):
        try:
            amt = float(tot.strip()) if tot and tot.strip() else 0.0
        except ValueError:
            amt = 0.0
        if cat.strip() or just.strip() or amt > 0:
            rows.append({
                "category": cat.strip(),
                "justification": just.strip(),
                "total": amt
            })

    # 2) Prepare the data dict
    estimate_data = {
        "claimant": claimant,
        "property": property_name,
        "estimator": estimator,
        "estimate_type": estimate_type,
        "date_entered": date_entered,
        "date_completed": date_completed,
        "rows": rows
    }

    # 3) Define logo path
    logo_path = os.path.abspath("app/static/logo2.jpg")


    pdf_url, excel_url = generate_pdf(
        logo_path=logo_path,
        client_name=client_name,
        claim_text=claim_text,
        estimate_data=estimate_data
    )

    # Persist permanent URLs
    record = FileRecord(
        id=str(uuid4()),
        client_name=client_name,
        file_path=pdf_url,
        pdf_path=pdf_url,
        excel_path=excel_url,
        uploaded_by=user.id
    )
    db.add(record)

    # 6) Track client addition
    track = ClientAddition(
        id=str(uuid4()),
        admin_id=user.id,
        client_name=client_name,
        timestamp=datetime.utcnow()
    )
    db.add(track)

    db.commit()

    # 7) Redirect to your download endpoint for the freshly-uploaded PDF
    return RedirectResponse(pdf_url, status_code=status.HTTP_303_SEE_OTHER)




@router.get("/clients", response_class=HTMLResponse)
def list_files(
    request: Request,
    month: Optional[int] = Query(None),
    year: Optional[int] = Query(None),
    uploader_email: Optional[str] = Query(None, alias="uploader_email"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):

    users = db.query(User).order_by(User.email).all()


    # — Files, optionally filtered by uploader_email
    files_q = db.query(FileRecord)
    if uploader_email:
        files_q = files_q.join(
            User, FileRecord.uploaded_by == User.id
        ).filter(User.email == uploader_email)
    files = files_q.order_by(FileRecord.created_at.desc()).all()

    # — ClientAddition events, filtered by uploader_email/month/year
    events_q = db.query(ClientAddition)
    if uploader_email:
        events_q = events_q.join(
            User, ClientAddition.admin_id == User.id
        ).filter(User.email == uploader_email)
    if month:
        events_q = events_q.filter(
            func.extract("month", ClientAddition.timestamp) == month
        )
    if year:
        events_q = events_q.filter(
            func.extract("year", ClientAddition.timestamp) == year
        )
    events = events_q.order_by(ClientAddition.timestamp.desc()).all()

    event_count = len(events)

    return templates.TemplateResponse(
        "clients.html",
        {
            "request": request,
            "users": users,                   # ← add this
            "files": files,
            "events": events,
            "filter_month": month,
            "filter_year": year,
            "filter_uploader": uploader_email,
            "event_count": event_count
        }
    )

@router.get("/admin/dashboard", response_class=HTMLResponse)
def admin_dashboard(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_admin)
):
    files = db.query(FileRecord).order_by(FileRecord.created_at.desc()).all()
    return templates.TemplateResponse(
        "admin_dashboard.html",
        {"request": request, "files": files}
    )


@router.post("/admin/add-client", response_class=RedirectResponse)
def add_client(
    client_name: str = Form(...),
    db: Session = Depends(get_db),
    user: User = Depends(require_admin)
):
    # Record new client
    record = FileRecord(
        client_name=client_name,
        pdf_path="",
        excel_path="",
        uploaded_by=user.id
    )
    db.add(record)

    # Track addition
    track = ClientAddition(
        id=str(uuid4()),
        admin_id=user.id,
        client_name=client_name,
        timestamp=datetime.utcnow()
    )
    db.add(track)

    db.commit()
    return RedirectResponse(
        url="/admin/dashboard",
        status_code=status.HTTP_303_SEE_OTHER
    )

