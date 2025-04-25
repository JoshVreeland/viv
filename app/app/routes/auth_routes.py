import uuid
from fastapi import (
    APIRouter, Request, Form, Depends,
    HTTPException, status, Response
)
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user_model import User
from app.schemas.user_schema import UserCreate
from app.utils.auth import hash_password, verify_password
from email.message import EmailMessage
from fastapi import BackgroundTasks
from app.dependencies import require_admin
import os
import smtplib

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


@router.post("/register", status_code=status.HTTP_201_CREATED)
def register(user: UserCreate, db: Session = Depends(get_db)):
    if db.query(User).filter(User.email == user.email).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    new_user = User(
        id=str(uuid.uuid4()),
        email=user.email,
        hashed_password=hash_password(user.password),
        is_admin=True,
        is_superadmin=False
    )
    db.add(new_user)
    db.commit()
    return {"message": "User registered successfully."}


@router.get("/login", response_class=HTMLResponse)
def login_get(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})


@router.post("/login", response_class=HTMLResponse)
def login_post(
    request: Request,
    response: Response,
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.email == email).first()
    if not user or not verify_password(password, user.hashed_password):
        # bad creds
        return templates.TemplateResponse(
            "login.html",
            {"request": request, "error": "Invalid email or password"},
            status_code=status.HTTP_401_UNAUTHORIZED
        )

    if not (user.is_admin or user.is_superadmin):
        # not allowed
        return templates.TemplateResponse(
            "login.html",
            {"request": request, "error": "Not authorized"},
            status_code=status.HTTP_403_FORBIDDEN
        )

    # in app/routes/auth_routes.py → login_post
    resp = RedirectResponse(url="/admin/dashboard", status_code=status.HTTP_302_FOUND)
    resp.set_cookie(
        key="user_id",
        value=str(user.id),
        httponly=True,
        path="/"                # ← make this explicit
    )
    return resp


@router.get("/logout")
def logout(response: Response):
    resp = RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)
    resp.delete_cookie("user_id")
    return resp

@router.get("/admin/add-admin", response_class=HTMLResponse)
def add_admin_get(request: Request):
    """
    Render a simple form where an existing admin can input an email
    to grant new admin access.
    """
    return templates.TemplateResponse("add_admin.html", {"request": request})

@router.get("/admin/add-admin", response_class=HTMLResponse)
def add_admin_get(request: Request):
    return templates.TemplateResponse("add_admin.html", {"request": request})

@router.post("/admin/add-admin", response_class=HTMLResponse)
def add_admin_post(
    request: Request,
    background_tasks: BackgroundTasks,
    email: str = Form(...),
    db: Session = Depends(get_db)
):
    # 1) Prevent duplicates
    if db.query(User).filter(User.email == email).first():
        return templates.TemplateResponse(
            "add_admin.html",
            {"request": request, "error": "That email’s already registered."},
            status_code=status.HTTP_400_BAD_REQUEST
        )

    # 2) Create temp password & user
    temp_pw = uuid.uuid4().hex[:8]
    new_user = User(
        id=str(uuid.uuid4()),
        email=email,
        hashed_password=hash_password(temp_pw),
        is_admin=True,
        is_superadmin=False
    )
    db.add(new_user)
    db.commit()

    # 3) Prepare email‐sending function with logging
    def send_invite_email():
        msg = EmailMessage()
        msg["Subject"] = "You’ve Been Invited as Admin on Merizō AI"
        msg["From"] = os.getenv("EMAIL_FROM")
        msg["To"] = email

        login_link = f"{os.getenv('APP_URL', 'http://localhost:8000')}/login"
        msg.set_content(f"""
Hello,

You have been granted ADMIN access on Merizō AI.

→ Login here: {login_link}
→ Email: {email}
→ Temporary password: {temp_pw}

After you log in, please change your password.

— The Merizō AI Team
""".strip())

        try:
            with smtplib.SMTP(os.getenv("SMTP_SERVER"), int(os.getenv("SMTP_PORT"))) as smtp:
                smtp.starttls()
                smtp.login(os.getenv("SMTP_USER"), os.getenv("SMTP_PASSWORD"))
                smtp.send_message(msg)
            print(f"[✅] Invite email sent to {email}")
        except Exception as e:
            print(f"[❌] Failed to send invite to {email}: {e}")

    # 4) Schedule it, then redirect immediately
    background_tasks.add_task(send_invite_email)
    return RedirectResponse("/admin/dashboard", status_code=status.HTTP_302_FOUND)

@router.get("/change-password", response_class=HTMLResponse)
def change_password_get(request: Request):
    return templates.TemplateResponse("change_password.html", {"request": request})

@router.post("/change-password", response_class=HTMLResponse)
def change_password_post(
    request: Request,
    old_password: str = Form(...),
    new_password: str = Form(...),
    confirm_password: str = Form(...),
    db: Session = Depends(get_db),
    user: User = Depends(require_admin)
):
    # verify current password
    if not verify_password(old_password, user.hashed_password):
        return templates.TemplateResponse(
            "change_password.html",
            {"request": request, "error": "Current password is incorrect."},
            status_code=status.HTTP_400_BAD_REQUEST
        )
    if new_password != confirm_password:
        return templates.TemplateResponse(
            "change_password.html",
            {"request": request, "error": "New passwords do not match."},
            status_code=status.HTTP_400_BAD_REQUEST
        )

    # update and save
    user.hashed_password = hash_password(new_password)
    db.add(user)
    db.commit()

    return RedirectResponse("/admin/dashboard", status_code=status.HTTP_302_FOUND)