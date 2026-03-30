from fastapi import FastAPI, HTTPException, Depends, status, Request, Form, Response, Cookie
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import create_engine, Column, Integer, String, Text, Boolean, DateTime, Float, ForeignKey, Enum, event
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session, relationship
from datetime import datetime, timedelta
from typing import Optional, List
import hashlib
import secrets
import os
import json
from pydantic import BaseModel, EmailStr
import enum
import httpx
from datetime import date
from sqlalchemy import Date

app = FastAPI(title="Трамплин - Карьерная платформа")

os.makedirs("static", exist_ok=True)
os.makedirs("templates", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


def from_json(value):
    if not value:
        return []
    try:
        if isinstance(value, str):
            return json.loads(value)
        return value
    except:
        return []


def to_json(value):
    try:
        return json.dumps(value, ensure_ascii=False)
    except:
        return "[]"


templates.env.filters['from_json'] = from_json
templates.env.filters['to_json'] = to_json

# ==================== НАСТРОЙКА БАЗЫ ДАННЫХ ====================
SQLALCHEMY_DATABASE_URL = "sqlite:///./tramplin.db"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    echo=False
)


# Добавляем обработку кодировки для SQLite
@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA encoding = 'UTF-8'")
    cursor.execute("PRAGMA foreign_keys = ON")
    cursor.close()


SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

SECRET_KEY = secrets.token_urlsafe(32)


class EmploymentType(enum.Enum):
    FULL_TIME = "Полная занятость"
    PART_TIME = "Частичная занятость"
    PROJECT = "Проектная работа"
    INTERNSHIP = "Стажировка"


class WorkFormat(enum.Enum):
    OFFICE = "В офисе"
    REMOTE = "Удаленно"
    HYBRID = "Гибрид"


class OpportunityType(enum.Enum):
    VACANCY = "Вакансия"
    INTERNSHIP = "Стажировка"
    MENTORING = "Менторская программа"
    EVENT = "Мероприятие"


class ResponseStatus(enum.Enum):
    PENDING = "На рассмотрении"
    ACCEPTED = "Принят"
    REJECTED = "Отклонен"
    RESERVE = "В резерве"


class VerificationStatus(enum.Enum):
    PENDING = "Ожидает проверки"
    VERIFIED = "Верифицирована"
    REJECTED = "Отклонена"


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    username = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    role = Column(String, default="seeker")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    verification_token = Column(String, nullable=True)
    seeker_profile = relationship("SeekerProfile", back_populates="user", uselist=False)
    employer_profile = relationship("EmployerProfile", back_populates="user", uselist=False)
    curator_profile = relationship("CuratorProfile", back_populates="user", uselist=False)


class SeekerProfile(Base):
    __tablename__ = "seeker_profiles"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True)
    full_name = Column(String, nullable=False, default="")
    university = Column(String, nullable=False, default="")
    course = Column(String, nullable=True)
    graduation_year = Column(Integer, nullable=True)
    about = Column(Text, nullable=True)
    skills = Column(Text, nullable=True)
    experience = Column(Text, nullable=True)
    github = Column(String, nullable=True)
    portfolio = Column(String, nullable=True)
    phone = Column(String, nullable=True)
    privacy_settings = Column(Text, default='{"show_profile": true, "show_responses": false}')
    user = relationship("User", back_populates="seeker_profile")
    responses = relationship("ApplicationResponse", back_populates="seeker")
    favorites = relationship("Favorite", back_populates="seeker")
    connections = relationship("Connection", foreign_keys="Connection.seeker_id", back_populates="seeker")


class EmployerProfile(Base):
    __tablename__ = "employer_profiles"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True)
    company_name = Column(String, nullable=False, default="")
    description = Column(Text, nullable=True)
    industry = Column(String, nullable=True)
    website = Column(String, nullable=True)
    social_links = Column(Text, nullable=True)
    inn = Column(String, nullable=True)
    verification_status = Column(Enum(VerificationStatus), default=VerificationStatus.PENDING)
    verification_docs = Column(Text, nullable=True)
    verified_at = Column(DateTime, nullable=True)
    logo = Column(String, nullable=True)
    address = Column(String, nullable=True)
    city = Column(String, nullable=True)
    user = relationship("User", back_populates="employer_profile")
    opportunities = relationship("Opportunity", back_populates="employer")


class CuratorProfile(Base):
    __tablename__ = "curator_profiles"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True)
    university = Column(String, nullable=True)
    position = Column(String, nullable=True)
    user = relationship("User", back_populates="curator_profile")
    moderated_opportunities = relationship("ModerationLog", foreign_keys="ModerationLog.curator_id")


class Opportunity(Base):
    __tablename__ = "opportunities"
    id = Column(Integer, primary_key=True, index=True)
    employer_id = Column(Integer, ForeignKey("employer_profiles.id"))
    title = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    type = Column(Enum(OpportunityType), nullable=False)
    work_format = Column(Enum(WorkFormat), nullable=False)
    employment_type = Column(Enum(EmploymentType), nullable=True)
    location = Column(String, nullable=False)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    salary_min = Column(Integer, nullable=True)
    salary_max = Column(Integer, nullable=True)
    requirements = Column(Text, nullable=True)
    tags = Column(Text, nullable=True)
    contacts = Column(Text, nullable=True)
    published_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(Date, nullable=True)
    event_date = Column(Date, nullable=True)
    is_active = Column(Boolean, default=True)
    is_moderated = Column(Boolean, default=False)
    views = Column(Integer, default=0)
    employer = relationship("EmployerProfile", back_populates="opportunities")
    responses = relationship("ApplicationResponse", back_populates="opportunity")
    favorites = relationship("Favorite", back_populates="opportunity")
    moderation_logs = relationship("ModerationLog", foreign_keys="ModerationLog.opportunity_id")
    is_online = Column(Boolean, default=False)  # True - онлайн, False - офлайн

class ApplicationResponse(Base):
    __tablename__ = "responses"
    id = Column(Integer, primary_key=True, index=True)
    opportunity_id = Column(Integer, ForeignKey("opportunities.id"))
    seeker_id = Column(Integer, ForeignKey("seeker_profiles.id"))
    message = Column(Text, nullable=True)
    status = Column(Enum(ResponseStatus), default=ResponseStatus.PENDING)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    opportunity = relationship("Opportunity", back_populates="responses")
    seeker = relationship("SeekerProfile", back_populates="responses")


class Favorite(Base):
    __tablename__ = "favorites"
    id = Column(Integer, primary_key=True, index=True)
    seeker_id = Column(Integer, ForeignKey("seeker_profiles.id"))
    opportunity_id = Column(Integer, ForeignKey("opportunities.id"))
    created_at = Column(DateTime, default=datetime.utcnow)
    seeker = relationship("SeekerProfile", back_populates="favorites")
    opportunity = relationship("Opportunity", back_populates="favorites")


class Connection(Base):
    __tablename__ = "connections"
    id = Column(Integer, primary_key=True, index=True)
    seeker_id = Column(Integer, ForeignKey("seeker_profiles.id"))
    friend_id = Column(Integer, ForeignKey("seeker_profiles.id"))
    status = Column(String, default="pending")
    created_at = Column(DateTime, default=datetime.utcnow)
    seeker = relationship("SeekerProfile", foreign_keys=[seeker_id], back_populates="connections")
    friend = relationship("SeekerProfile", foreign_keys=[friend_id])


class ModerationLog(Base):
    __tablename__ = "moderation_logs"
    id = Column(Integer, primary_key=True, index=True)
    curator_id = Column(Integer, ForeignKey("curator_profiles.id"))
    opportunity_id = Column(Integer, ForeignKey("opportunities.id"), nullable=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    action = Column(String, nullable=False)
    comment = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    curator = relationship("CuratorProfile", foreign_keys=[curator_id])
    opportunity = relationship("Opportunity", foreign_keys=[opportunity_id])
    user = relationship("User", foreign_keys=[user_id])


class Tag(Base):
    __tablename__ = "tags"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)
    category = Column(String, nullable=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    is_system = Column(Boolean, default=False)


class Notification(Base):
    __tablename__ = "notifications"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    type = Column(String, nullable=False)
    title = Column(String, nullable=False)
    message = Column(Text, nullable=False)
    data = Column(Text, nullable=True)
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    user = relationship("User")


class Message(Base):
    __tablename__ = "messages"
    id = Column(Integer, primary_key=True, index=True)
    sender_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    receiver_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    opportunity_id = Column(Integer, ForeignKey("opportunities.id"), nullable=True)
    text = Column(Text, nullable=False)
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    sender = relationship("User", foreign_keys=[sender_id])
    receiver = relationship("User", foreign_keys=[receiver_id])
    opportunity = relationship("Opportunity")


class EventRegistration(Base):
    __tablename__ = "event_registrations"
    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(Integer, ForeignKey("opportunities.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    status = Column(String, default="registered")
    registered_at = Column(DateTime, default=datetime.utcnow)

    event = relationship("Opportunity")
    user = relationship("User")


Base.metadata.create_all(bind=engine)


class UserCreate(BaseModel):
    email: EmailStr
    username: str
    password: str
    role: str


class UserLogin(BaseModel):
    username: str
    password: str


class OpportunityCreate(BaseModel):
    title: str
    description: str
    type: OpportunityType
    work_format: WorkFormat
    employment_type: Optional[EmploymentType] = None
    location: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    salary_min: Optional[int] = None
    salary_max: Optional[int] = None
    requirements: Optional[str] = None
    tags: List[str] = []
    contacts: dict = {}
    expires_at: Optional[date] = None
    event_date: Optional[date] = None


class SeekerProfileCreate(BaseModel):
    full_name: str
    university: str
    course: Optional[str] = None
    graduation_year: Optional[int] = None
    about: Optional[str] = None
    skills: List[str] = []
    experience: Optional[List[dict]] = None
    github: Optional[str] = None
    portfolio: Optional[str] = None
    phone: Optional[str] = None


def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


def verify_password(password: str, hash: str) -> bool:
    return hash_password(password) == hash


def create_verification_token():
    return secrets.token_urlsafe(32)


sessions = {}
SESSION_EXPIRE_DAYS = 7


def create_session(user_id: int) -> str:
    token = secrets.token_urlsafe(32)
    sessions[token] = {
        "user_id": user_id,
        "expires": datetime.now() + timedelta(days=SESSION_EXPIRE_DAYS)
    }
    return token


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_current_user(request: Request, db: Session = Depends(get_db)):
    session_token = request.cookies.get("session_token")
    if not session_token or session_token not in sessions:
        return None
    session = sessions[session_token]
    if session["expires"] < datetime.now():
        del sessions[session_token]
        return None
    user = db.query(User).filter(User.id == session["user_id"]).first()
    return user


def get_user_role_safe(user):
    """Безопасное получение роли пользователя в виде строки"""
    if user is None:
        return None
    return user.role


async def geocode_address(address: str) -> tuple:
    if not address:
        return None, None
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(
                "https://nominatim.openstreetmap.org/search",
                params={"q": address, "format": "json", "limit": 1, "addressdetails": 1},
                headers={"User-Agent": "Tramplin/1.0 (https://tramplin.ru)"}
            )
            if response.status_code == 200:
                data = response.json()
                if data:
                    return float(data[0]["lat"]), float(data[0]["lon"])
    except Exception as e:
        print(f"Ошибка геокодирования: {e}")
    return None, None


# ==================== ГЛАВНАЯ СТРАНИЦА ====================

@app.get("/", response_class=HTMLResponse)
async def index(request: Request, db: Session = Depends(get_db)):
    opportunities = db.query(Opportunity).filter(
        Opportunity.is_active == True, Opportunity.is_moderated == True
    ).order_by(Opportunity.published_at.desc()).limit(50).all()
    tags = db.query(Tag).all()
    current_user = get_current_user(request, db)
    responses_count = 0
    favorites_count = 0
    if current_user and get_user_role_safe(current_user) == 'seeker' and current_user.seeker_profile:
        responses_count = db.query(ApplicationResponse).filter(
            ApplicationResponse.seeker_id == current_user.seeker_profile.id
        ).count()
        favorites_count = db.query(Favorite).filter(
            Favorite.seeker_id == current_user.seeker_profile.id
        ).count()
    return templates.TemplateResponse("index.html", {
        "request": request,
        "opportunities": opportunities,
        "tags": tags,
        "opportunity_types": [t.value for t in OpportunityType],
        "work_formats": [f.value for f in WorkFormat],
        "employment_types": [e.value for e in EmploymentType],
        "current_user": current_user,
        "responses_count": responses_count,
        "favorites_count": favorites_count
    })


# ==================== API ДЛЯ ВАКАНСИЙ ====================

@app.get("/api/opportunities")
async def get_opportunities(
        request: Request,
        db: Session = Depends(get_db),
        type: Optional[str] = None,
        format: Optional[str] = None,
        tag: Optional[str] = None,
        city: Optional[str] = None,
        min_salary: Optional[int] = None,
        event_format: Optional[str] = None
):
    """Получить список вакансий и мероприятий"""
    try:
        print("🔍 API вызван с фильтрами:", type, format, city, min_salary, event_format)
        
                # ========== ДОБАВЬТЕ ЭТИ СТРОКИ ==========
        current_user = get_current_user(request, db)
        favorite_ids = set()
        if current_user and current_user.seeker_profile:
            favorites = db.query(Favorite).filter(
                Favorite.seeker_id == current_user.seeker_profile.id
            ).all()
            favorite_ids = {fav.opportunity_id for fav in favorites}
        
        query = db.query(Opportunity).filter(
            Opportunity.is_active == True,
            Opportunity.is_moderated == True
        )
        
        if type:
            try:
                if type == 'VACANCY':
                    query = query.filter(Opportunity.type == OpportunityType.VACANCY)
                elif type == 'INTERNSHIP':
                    query = query.filter(Opportunity.type == OpportunityType.INTERNSHIP)
                elif type == 'MENTORING':
                    query = query.filter(Opportunity.type == OpportunityType.MENTORING)
                elif type == 'EVENT':
                    query = query.filter(Opportunity.type == OpportunityType.EVENT)
            except:
                pass
        
        if format:
            try:
                if format == 'OFFICE':
                    query = query.filter(Opportunity.work_format == WorkFormat.OFFICE)
                elif format == 'REMOTE':
                    query = query.filter(Opportunity.work_format == WorkFormat.REMOTE)
                elif format == 'HYBRID':
                    query = query.filter(Opportunity.work_format == WorkFormat.HYBRID)
            except:
                pass
        
        if city and city.strip():
            query = query.filter(Opportunity.location.contains(city.strip()))
        
        if min_salary and min_salary > 0:
            query = query.filter(
                Opportunity.salary_min >= min_salary,
                Opportunity.type != OpportunityType.EVENT
            )
        
        if event_format and event_format in ['online', 'offline']:
            is_online_value = (event_format == 'online')
            query = query.filter(
                Opportunity.type == OpportunityType.EVENT,
                Opportunity.is_online == is_online_value
            )
            if not type:
                query = query.filter(Opportunity.type == OpportunityType.EVENT)
        
        opportunities = query.all()
        
        print(f"✅ Найдено записей: {len(opportunities)}")
        
        result = []
        for opp in opportunities:
            # Для мероприятий
            if opp.type == OpportunityType.EVENT:
                # Определяем формат
                is_online_val = getattr(opp, 'is_online', False)
                display_format = "Заочно" if is_online_val else "Очно"
                
                result.append({
                    "id": opp.id,
                    "title": opp.title,
                    "company": opp.employer.company_name if opp.employer else "Организатор",
                    "location": opp.location,
                    "latitude": opp.latitude,
                    "longitude": opp.longitude,
                    "type": "Мероприятие",
                    "work_format": display_format,
                    "salary_min": None,
                    "salary_max": None,
                    "tags": json.loads(opp.tags) if opp.tags else [],
                    "description": opp.description[:200] if opp.description else "",
                    "is_event": True,
                    "event_date": opp.event_date.strftime('%d.%m.%Y') if opp.event_date else "",
                    "is_online": is_online_val,
                    "is_favorite": opp.id in favorite_ids
                })
            else:
                # Для вакансий
                result.append({
                    "id": opp.id,
                    "title": opp.title,
                    "company": opp.employer.company_name if opp.employer else "Компания",
                    "location": opp.location,
                    "latitude": opp.latitude,
                    "longitude": opp.longitude,
                    "type": opp.type.value,
                    "work_format": opp.work_format.value,
                    "salary_min": opp.salary_min,
                    "salary_max": opp.salary_max,
                    "tags": json.loads(opp.tags) if opp.tags else [],
                    "description": opp.description[:200] if opp.description else "",
                    "is_event": False,
                    "is_favorite": opp.id in favorite_ids
                })
        
        return result
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()
        return []


@app.get("/opportunity/{opportunity_id}", response_class=HTMLResponse)
async def opportunity_detail(request: Request, opportunity_id: int, db: Session = Depends(get_db)):
    opportunity = db.query(Opportunity).filter(Opportunity.id == opportunity_id).first()
    if not opportunity:
        raise HTTPException(status_code=404, detail="Вакансия не найдена")
    opportunity.views += 1
    db.commit()
    current_user = get_current_user(request, db)
    seeker_profile_id = None
    if current_user and get_user_role_safe(current_user) == 'seeker' and current_user.seeker_profile:
        seeker_profile_id = current_user.seeker_profile.id
    return templates.TemplateResponse("opportunity_detail.html", {
        "request": request,
        "opportunity": opportunity,
        "tags": json.loads(opportunity.tags) if opportunity.tags else [],
        "contacts": json.loads(opportunity.contacts) if opportunity.contacts else {},
        "current_user": current_user,
        "seeker_profile_id": seeker_profile_id
    })


# ==================== РЕГИСТРАЦИЯ И АВТОРИЗАЦИЯ ====================

@app.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    return templates.TemplateResponse("register.html", {"request": request})


@app.post("/api/register", response_model=None)
async def register(user_data: UserCreate, request: Request, db: Session = Depends(get_db)):
    try:
        if db.query(User).filter(User.email == user_data.email).first():
            raise HTTPException(status_code=400, detail="Email уже зарегистрирован")
        if db.query(User).filter(User.username == user_data.username).first():
            raise HTTPException(status_code=400, detail="Имя пользователя уже занято")
        data = await request.json()

        # Преобразуем роль в строку
        role_str = user_data.role.lower()

        # Обычные пользователи НЕ МОГУТ зарегистрироваться как администратор
        if role_str in ['admin']:
            raise HTTPException(status_code=403, detail="Регистрация администраторов недоступна")

        if role_str not in ['seeker', 'employer', 'curator']:
            role_str = 'seeker'

        user = User(
            email=user_data.email,
            username=user_data.username,
            password_hash=hash_password(user_data.password),
            role=role_str,
            verification_token=create_verification_token()
        )
        db.add(user)
        db.flush()

        if role_str == 'seeker':
            profile = SeekerProfile(
                user_id=user.id,
                full_name="",
                university="",
                privacy_settings='{"show_profile": true, "show_responses": false}'
            )
            db.add(profile)
        elif role_str == 'employer':
            profile = EmployerProfile(
                user_id=user.id,
                company_name=data.get("company_name", ""),
                inn=data.get("inn", ""),
                website=data.get("website", ""),
                industry=data.get("industry", ""),
                description="",
                address="",
                city="",
                verification_status=VerificationStatus.PENDING
            )
            db.add(profile)
        elif role_str == 'curator':
            profile = CuratorProfile(
                user_id=user.id,
                university=data.get("university", "Не указан"),
                position=data.get("position", "Модератор")
            )
            db.add(profile)

        db.commit()
        db.refresh(user)
        return {"message": "Регистрация успешна", "user_id": user.id, "success": True}
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Ошибка регистрации: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})


@app.post("/api/login", response_model=None)
async def login(credentials: UserLogin, response: Response, db: Session = Depends(get_db)):
    try:
        user = db.query(User).filter(
            (User.username == credentials.username) |
            (User.email == credentials.username)
        ).first()

        if not user:
            raise HTTPException(status_code=401, detail="Пользователь не найден")
        if not verify_password(credentials.password, user.password_hash):
            raise HTTPException(status_code=401, detail="Неверный пароль")
        if not user.is_active:
            raise HTTPException(status_code=403, detail="Аккаунт заблокирован")

        session_token = create_session(user.id)
        response.set_cookie(
            key="session_token",
            value=session_token,
            httponly=True,
            max_age=60 * 60 * 24 * SESSION_EXPIRE_DAYS,
            secure=False,
            samesite="lax"
        )

        role_str = user.role

        # Определяем URL для редиректа
        if role_str == 'seeker':
            redirect_url = f"/profile/seeker/{user.id}"
        elif role_str == 'employer':
            redirect_url = f"/profile/employer/{user.id}"
        elif role_str == 'curator':
            redirect_url = "/curator/dashboard"
        elif role_str == 'admin':
            redirect_url = "/admin/dashboard"
        else:
            redirect_url = "/"

        return {
            "success": True,
            "message": "Вход выполнен успешно",
            "user_id": user.id,
            "username": user.username,
            "role": role_str,
            "redirect_url": redirect_url
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Ошибка входа: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


# ==================== ЛИЧНЫЕ КАБИНЕТЫ ====================

@app.get("/profile/seeker/{user_id}", response_class=HTMLResponse)
async def seeker_profile(request: Request, user_id: int, db: Session = Depends(get_db)):
    try:
        current_user = get_current_user(request, db)
        if not current_user:
            return RedirectResponse(url="/login", status_code=302)

        current_role = get_user_role_safe(current_user)

        if current_user.id != user_id and current_role.lower() != 'admin':
            return RedirectResponse(url=f"/profile/seeker/{current_user.id}", status_code=302)

        user = db.query(User).filter(User.id == user_id, User.role == 'seeker').first()
        if not user:
            raise HTTPException(status_code=404, detail="Профиль не найден")

        profile = user.seeker_profile
        if not profile:
            profile = SeekerProfile(
                user_id=user.id,
                full_name=user.username,
                university="Не указан",
                privacy_settings='{"show_profile": true, "show_responses": false}'
            )
            db.add(profile)
            db.commit()
            db.refresh(profile)
        responses = db.query(ApplicationResponse).filter(ApplicationResponse.seeker_id == profile.id).all()
        favorites = db.query(Favorite).filter(Favorite.seeker_id == profile.id).all()
        connections = db.query(Connection).filter(
            (Connection.seeker_id == profile.id) | (Connection.friend_id == profile.id),
            Connection.status == "accepted"
        ).all()
        skills = json.loads(profile.skills) if profile.skills else []
        return templates.TemplateResponse("seeker_dashboard.html", {
            "request": request,
            "user": user,
            "profile": profile,
            "responses": responses,
            "favorites": favorites,
            "connections": connections,
            "skills": skills,
            "current_user": current_user
        })
    except Exception as e:
        print(f"❌ Ошибка профиля соискателя: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/profile/seeker/view/{seeker_id}", response_class=HTMLResponse)
async def view_seeker_profile(
        request: Request,
        seeker_id: int,
        db: Session = Depends(get_db)
):
    """Просмотр профиля другого соискателя"""
    import traceback
    import json

    try:
        current_user = get_current_user(request, db)

        if not current_user:
            return HTMLResponse(content="""
            <!DOCTYPE html>
            <html>
            <head><title>Ошибка</title></head>
            <body>
                <h1>Не авторизован</h1>
                <a href="/login">Войти</a>
            </body>
            </html>
            """)

        seeker = db.query(SeekerProfile).filter(SeekerProfile.id == seeker_id).first()
        if not seeker:
            return HTMLResponse(content=f"<h1>Профиль {seeker_id} не найден</h1>")

        user = db.query(User).filter(User.id == seeker.user_id).first()
        if not user:
            return HTMLResponse(content=f"<h1>Пользователь не найден</h1>")

        # Безопасное преобразование строк
        def safe_str(value):
            if value is None:
                return ""
            if isinstance(value, bytes):
                try:
                    return value.decode('utf-8')
                except:
                    try:
                        return value.decode('cp1251')
                    except:
                        return str(value)
            return str(value)

        # Получаем настройки приватности
        privacy_settings = safe_str(seeker.privacy_settings)
        try:
            privacy = json.loads(privacy_settings) if privacy_settings else {"show_profile": True,
                                                                             "show_responses": True}
        except:
            privacy = {"show_profile": True, "show_responses": True}

        show_profile = privacy.get("show_profile", True)
        show_responses = privacy.get("show_responses", True)

        # Проверяем, является ли текущий пользователь другом
        is_friend = False
        if current_user and current_user.seeker_profile:
            connection = db.query(Connection).filter(
                ((Connection.seeker_id == current_user.seeker_profile.id) & (Connection.friend_id == seeker_id)) |
                ((Connection.seeker_id == seeker_id) & (Connection.friend_id == current_user.seeker_profile.id)),
                Connection.status == "accepted"
            ).first()
            is_friend = connection is not None

        is_owner = current_user and current_user.id == user.id

        # Если профиль скрыт и пользователь не друг и не владелец
        if not show_profile and not is_friend and not is_owner:
            return HTMLResponse(content=f"""
            <!DOCTYPE html>
            <html>
            <head>
                <title>Профиль скрыт - Трамплин</title>
                <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
                <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
            </head>
            <body style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); min-height: 100vh;">
                <div class="container mt-5">
                    <div class="card text-center">
                        <div class="card-body p-5">
                            <i class="fas fa-lock fa-4x text-muted mb-3"></i>
                            <h3>Профиль скрыт</h3>
                            <p class="text-muted">Пользователь <strong>{seeker.full_name}</strong> ограничил доступ к своему профилю.</p>
                            <p class="text-muted">Добавьте пользователя в контакты, чтобы увидеть информацию.</p>
                            <button class="btn btn-primary mt-3" onclick="sendFriendRequest({seeker_id})" id="addToContactsBtn">
                                <i class="fas fa-user-plus"></i> Добавить в контакты
                            </button>
                            <a href="/" class="btn btn-secondary mt-3 ms-2">На главную</a>
                        </div>
                    </div>
                </div>
                <script>
                    async function sendFriendRequest(seekerId) {{
                        try {{
                            const response = await fetch(`/api/connection/request?friend_id=${{seekerId}}`, {{
                                method: 'POST',
                                headers: {{ 'Content-Type': 'application/json' }}
                            }});
                            const data = await response.json();
                            if (response.ok) {{
                                alert('✅ ' + data.message);
                                const btn = document.getElementById('addToContactsBtn');
                                if (btn) btn.disabled = true;
                            }} else {{
                                alert('❌ Ошибка: ' + (data.detail || data.message));
                            }}
                        }} catch (error) {{
                            alert('❌ Ошибка соединения');
                        }}
                    }}
                </script>
            </body>
            </html>
            """)

        # ========== ПРОФИЛЬ ОТКРЫТ - ПОКАЗЫВАЕМ ВСЮ ИНФОРМАЦИЮ ==========

        # Получаем отклики
        responses_html = ""
        can_see_responses = is_owner or is_friend or show_responses

        if can_see_responses:
            responses = db.query(ApplicationResponse).filter(
                ApplicationResponse.seeker_id == seeker_id
            ).order_by(ApplicationResponse.created_at.desc()).all()

            if responses:
                for resp in responses:
                    opportunity = db.query(Opportunity).filter(Opportunity.id == resp.opportunity_id).first()
                    if opportunity and opportunity.type != OpportunityType.EVENT:
                        status_class = ""
                        if resp.status.value == "На рассмотрении":
                            status_class = "badge-warning"
                        elif resp.status.value == "Принят":
                            status_class = "badge-success"
                        elif resp.status.value == "Отклонен":
                            status_class = "badge-danger"
                        else:
                            status_class = "badge-info"

                        responses_html += f"""
                        <div class="list-group-item" style="cursor: pointer;" onclick="location.href='/opportunity/{resp.opportunity_id}'">
                            <div class="d-flex justify-content-between align-items-center">
                                <div>
                                    <strong>{opportunity.title}</strong><br>
                                    <small class="text-muted">{opportunity.employer.company_name if opportunity.employer else "Компания"}</small>
                                </div>
                                <div class="text-end">
                                    <span class="badge {status_class}">{resp.status.value}</span><br>
                                    <small class="text-muted">{resp.created_at.strftime('%d.%m.%Y')}</small>
                                </div>
                            </div>
                        </div>
                        """
            else:
                responses_html = '<p class="text-muted">Нет откликов</p>'
        else:
            responses_html = '<p class="text-muted"><i class="fas fa-lock me-1"></i> Пользователь скрыл свои отклики</p>'

        # Получаем мероприятия
        events_html = ""
        registrations = db.query(EventRegistration).filter(
            EventRegistration.user_id == user.id,
            EventRegistration.status == "registered"
        ).all()

        if registrations:
            for reg in registrations:
                event = db.query(Opportunity).filter(Opportunity.id == reg.event_id).first()
                if event:
                    work_format_icon = ""
                    if event.work_format.value == "Очно":
                        work_format_icon = "🏢"
                    elif event.work_format.value == "Заочно":
                        work_format_icon = "💻"
                    else:
                        work_format_icon = "🔄"

                    events_html += f"""
                    <div class="list-group-item" style="cursor: pointer;" onclick="location.href='/opportunity/{event.id}'">
                        <div class="d-flex justify-content-between align-items-center">
                            <div>
                                <strong>{event.title}</strong><br>
                                <small class="text-muted">
                                    {work_format_icon} {event.work_format.value} | 📍 {event.location[:50] if event.location else "Не указано"}
                                </small>
                            </div>
                            <div class="text-end">
                                <span class="badge bg-primary">
                                    <i class="fas fa-calendar"></i> {event.event_date.strftime('%d.%m.%Y') if event.event_date else "Дата не указана"}
                                </span><br>
                                <small class="text-muted">Зарегистрирован: {reg.registered_at.strftime('%d.%m.%Y')}</small>
                            </div>
                        </div>
                    </div>
                    """
        else:
            events_html = '<p class="text-muted">Нет записей на мероприятия</p>'

        # Парсим навыки
        skills_html = ""
        if seeker.skills:
            try:
                skills_list = json.loads(seeker.skills)
                for skill in skills_list:
                    skills_html += f'<span class="skill-tag">{skill}</span>'
                if not skills_list:
                    skills_html = '<p class="text-muted">Навыки не добавлены</p>'
            except:
                skills_html = '<p class="text-muted">Навыки не добавлены</p>'
        else:
            skills_html = '<p class="text-muted">Навыки не добавлены</p>'

        # Формируем страницу
        html = f"""
        <!DOCTYPE html>
        <html lang="ru">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>{seeker.full_name} - Трамплин</title>
            <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
            <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
            <style>
                body {{
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    min-height: 100vh;
                    padding-bottom: 50px;
                }}
                .navbar {{
                    background: white !important;
                    box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                }}
                .navbar-brand {{
                    font-weight: bold;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    -webkit-background-clip: text;
                    -webkit-text-fill-color: transparent;
                }}
                .profile-card {{
                    background: white;
                    border-radius: 20px;
                    overflow: hidden;
                    box-shadow: 0 10px 30px rgba(0,0,0,0.2);
                    margin-top: 30px;
                }}
                .profile-header {{
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                    padding: 30px;
                    text-align: center;
                }}
                .profile-header i {{
                    font-size: 5rem;
                    margin-bottom: 15px;
                }}
                .profile-header h2 {{
                    margin-bottom: 5px;
                }}
                .profile-body {{
                    padding: 30px;
                }}
                .info-section {{
                    margin-bottom: 25px;
                }}
                .info-section h5 {{
                    color: #667eea;
                    margin-bottom: 15px;
                    padding-bottom: 8px;
                    border-bottom: 2px solid #e2e8f0;
                }}
                .info-row {{
                    display: flex;
                    padding: 8px 0;
                    border-bottom: 1px solid #f1f5f9;
                }}
                .info-label {{
                    width: 120px;
                    font-weight: 600;
                    color: #475569;
                }}
                .info-value {{
                    flex: 1;
                    color: #1e293b;
                }}
                .skill-tag {{
                    display: inline-block;
                    padding: 5px 12px;
                    background: #e3f2fd;
                    color: #1976d2;
                    border-radius: 20px;
                    font-size: 0.85rem;
                    margin-right: 8px;
                    margin-bottom: 8px;
                }}
                .list-group-item {{
                    transition: all 0.2s;
                    cursor: pointer;
                }}
                .list-group-item:hover {{
                    background: #f8f9fa;
                    transform: translateX(5px);
                    border-color: #667eea;
                }}
                .badge-warning {{ background: #fff3cd; color: #856404; }}
                .badge-success {{ background: #d4edda; color: #155724; }}
                .badge-danger {{ background: #f8d7da; color: #721c24; }}
                .badge-info {{ background: #cce5ff; color: #004085; }}
                .btn-primary {{
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    border: none;
                }}
                .btn-primary:hover {{
                    transform: translateY(-2px);
                    box-shadow: 0 5px 15px rgba(102, 126, 234, 0.4);
                }}
            </style>
        </head>
        <body>
            <nav class="navbar navbar-expand-lg navbar-light bg-white">
                <div class="container">
                    <a class="navbar-brand" href="/">
                        <i class="fas fa-rocket me-2"></i>Трамплин
                    </a>
                    <div class="ms-auto">
                        <a href="/" class="btn btn-outline-primary me-2">
                            <i class="fas fa-home"></i> На главную
                        </a>
                        <a href="/profile/seeker/{current_user.id}" class="btn btn-primary">
                            <i class="fas fa-user"></i> Мой профиль
                        </a>
                    </div>
                </div>
            </nav>

            <div class="container">
                <div class="profile-card">
                    <div class="profile-header">
                        <i class="fas fa-user-circle"></i>
                        <h2>{seeker.full_name}</h2>
                        <p class="mb-0">{seeker.university or 'Университет не указан'}</p>
                    </div>
                    <div class="profile-body">
                        <div class="row">
                            <div class="col-md-6">
                                <div class="info-section">
                                    <h5><i class="fas fa-info-circle me-2"></i>Основная информация</h5>
                                    <div class="info-row">
                                        <div class="info-label">Email:</div>
                                        <div class="info-value">{user.email or 'Не указан'}</div>
                                    </div>
                                    <div class="info-row">
                                        <div class="info-label">Телефон:</div>
                                        <div class="info-value">{seeker.phone or 'Не указан'}</div>
                                    </div>
                                    <div class="info-row">
                                        <div class="info-label">Курс:</div>
                                        <div class="info-value">{seeker.course or 'Не указан'}</div>
                                    </div>
                                    <div class="info-row">
                                        <div class="info-label">Год выпуска:</div>
                                        <div class="info-value">{seeker.graduation_year or 'Не указан'}</div>
                                    </div>
                                    {f'<div class="info-row"><div class="info-label">GitHub:</div><div class="info-value"><a href="{seeker.github}" target="_blank">{seeker.github}</a></div></div>' if seeker.github else ''}
                                </div>
                            </div>
                            <div class="col-md-6">
                                <div class="info-section">
                                    <h5><i class="fas fa-align-left me-2"></i>О себе</h5>
                                    <p>{seeker.about or 'Информация не заполнена'}</p>
                                </div>
                                <div class="info-section">
                                    <h5><i class="fas fa-code me-2"></i>Навыки</h5>
                                    <div>
                                        {skills_html}
                                    </div>
                                </div>
                            </div>
                        </div>

                        <div class="info-section">
                            <h5><i class="fas fa-paper-plane me-2"></i>Отклики на вакансии</h5>
                            {responses_html}
                        </div>

                        <div class="info-section">
                            <h5><i class="fas fa-calendar-alt me-2"></i>Участие в мероприятиях</h5>
                            {events_html}
                        </div>

                        <div class="mt-4 d-flex gap-2">
                            {'<button class="btn btn-success" disabled><i class="fas fa-check"></i> В контактах</button>' if is_friend else ''}
                            {'<button class="btn btn-primary" onclick="sendFriendRequest()" id="addToContactsBtn"><i class="fas fa-user-plus"></i> Добавить в контакты</button>' if not is_friend and not is_owner else ''}
                            <a href="javascript:history.back()" class="btn btn-secondary">
                                <i class="fas fa-arrow-left"></i> Назад
                            </a>
                        </div>
                    </div>
                </div>
            </div>

            <script>
                const seekerProfileId = {seeker_id};
                const currentUserId = {current_user.id};

                async function sendFriendRequest() {{
                    try {{
                        const response = await fetch(`/api/connection/request?friend_id=${{seekerProfileId}}`, {{
                            method: 'POST',
                            headers: {{ 'Content-Type': 'application/json' }}
                        }});
                        const data = await response.json();
                        if (response.ok) {{
                            alert('✅ ' + data.message);
                            const btn = document.getElementById('addToContactsBtn');
                            if (btn) {{
                                btn.disabled = true;
                                btn.innerHTML = '<i class="fas fa-clock"></i> Запрос отправлен';
                            }}
                        }} else {{
                            alert('❌ Ошибка: ' + (data.detail || data.message || 'Неизвестная ошибка'));
                        }}
                    }} catch (error) {{
                        console.error('Ошибка:', error);
                        alert('❌ Ошибка соединения: ' + error.message);
                    }}
                }}
            </script>
        </body>
        </html>
        """

        return HTMLResponse(content=html)

    except Exception as e:
        error_details = traceback.format_exc()
        print(error_details)
        return HTMLResponse(content=f"""
        <!DOCTYPE html>
        <html>
        <head><title>Ошибка</title></head>
        <body>
            <h1>Ошибка:</h1>
            <pre>{e}</pre>
            <hr>
            <pre>{error_details}</pre>
        </body>
        </html>
        """)


@app.get("/profile/employer/{user_id}", response_class=HTMLResponse)
async def employer_profile(request: Request, user_id: int, db: Session = Depends(get_db)):
    try:
        user = db.query(User).filter(User.id == user_id, User.role == 'employer').first()
        if not user:
            raise HTTPException(status_code=404, detail="Профиль не найден")
        profile = user.employer_profile
        if not profile:
            profile = EmployerProfile(user_id=user.id, company_name=user.username,
                                      verification_status=VerificationStatus.PENDING)
            db.add(profile)
            db.commit()
        opportunities = db.query(Opportunity).filter(Opportunity.employer_id == profile.id).all()
        all_responses = []
        for opp in opportunities:
            responses = db.query(ApplicationResponse).filter(ApplicationResponse.opportunity_id == opp.id).all()
            for resp in responses:
                seeker = db.query(SeekerProfile).filter(SeekerProfile.id == resp.seeker_id).first()
                resp.seeker_name = seeker.full_name if seeker else "Пользователь"
                resp.opportunity_title = opp.title
                all_responses.append(resp)
        social_links = json.loads(profile.social_links) if profile.social_links else {}
        return templates.TemplateResponse("employer_dashboard.html", {
            "request": request, "user": user, "profile": profile, "opportunities": opportunities,
            "all_responses": all_responses, "total_responses": len(all_responses), "social_links": social_links
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/employer/profile/update", response_model=None)
async def update_employer_profile(user_id: int = Form(...), company_name: str = Form(None),
                                  industry: str = Form(None), website: str = Form(None),
                                  address: str = Form(None), city: str = Form(None),
                                  description: str = Form(None), inn: str = Form(None),
                                  db: Session = Depends(get_db)):
    try:
        profile = db.query(EmployerProfile).filter(EmployerProfile.user_id == user_id).first()
        if not profile:
            raise HTTPException(status_code=404, detail="Профиль не найден")
        if company_name: profile.company_name = company_name
        if industry: profile.industry = industry
        if website: profile.website = website
        if address: profile.address = address
        if city: profile.city = city
        if description: profile.description = description
        if inn: profile.inn = inn
        db.commit()
        return {"message": "Профиль обновлен", "success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== ОТКЛИКИ И ИЗБРАННОЕ ====================

@app.post("/api/response/create", response_model=None)
async def create_response(request: Request, db: Session = Depends(get_db)):
    try:
        data = await request.json()
        opportunity_id = data.get("opportunity_id")
        seeker_id = data.get("seeker_id")
        message = data.get("message", "")
        if not opportunity_id or not seeker_id:
            raise HTTPException(status_code=400, detail="Не указаны opportunity_id or seeker_id")
        opportunity = db.query(Opportunity).filter(Opportunity.id == opportunity_id).first()
        if not opportunity:
            raise HTTPException(status_code=404, detail="Вакансия не найдена")
        seeker = db.query(SeekerProfile).filter(SeekerProfile.id == seeker_id).first()
        if not seeker:
            user = db.query(User).filter(User.id == seeker_id, User.role == 'seeker').first()
            if user and user.seeker_profile:
                seeker = user.seeker_profile
            else:
                raise HTTPException(status_code=404, detail="Соискатель не найден")
        existing = db.query(ApplicationResponse).filter(
            ApplicationResponse.opportunity_id == opportunity_id,
            ApplicationResponse.seeker_id == seeker.id
        ).first()
        if existing:
            raise HTTPException(status_code=400, detail="Вы уже откликались на эту вакансию")
        response = ApplicationResponse(
            opportunity_id=opportunity_id,
            seeker_id=seeker.id,
            message=message,
            status=ResponseStatus.PENDING
        )
        db.add(response)
        db.commit()
        return {"message": "Отклик успешно отправлен!", "success": True}
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/response/update-status", response_model=None)
async def update_response_status(request: Request, db: Session = Depends(get_db)):
    try:
        data = await request.json()
        response_id = data.get("response_id")
        status = data.get("status")
        employer_id = data.get("employer_id")
        if not response_id or not status or not employer_id:
            raise HTTPException(status_code=400, detail="Не указаны все необходимые параметры")
        employer = db.query(EmployerProfile).filter(EmployerProfile.id == employer_id).first()
        if not employer:
            raise HTTPException(status_code=403, detail="Доступ запрещен. Работодатель не найден.")
        response = db.query(ApplicationResponse).filter(ApplicationResponse.id == response_id).first()
        if not response:
            raise HTTPException(status_code=404, detail="Отклик не найден")
        opportunity = db.query(Opportunity).filter(Opportunity.id == response.opportunity_id).first()
        if opportunity.employer_id != employer_id:
            raise HTTPException(status_code=403, detail="Вы не можете изменять статус этого отклика")
        if status == "accepted":
            response.status = ResponseStatus.ACCEPTED
            message = "Отклик принят"
        elif status == "rejected":
            response.status = ResponseStatus.REJECTED
            message = "Отклик отклонен"
        elif status == "reserve":
            response.status = ResponseStatus.RESERVE
            message = "Отклик добавлен в резерв"
        else:
            raise HTTPException(status_code=400, detail="Неверный статус")
        db.commit()
        return {"message": message, "success": True}
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/favorite/toggle", response_model=None)
async def toggle_favorite(request: Request, db: Session = Depends(get_db)):
    try:
        data = await request.json()
        opportunity_id = data.get("opportunity_id")
        seeker_id = data.get("seeker_id")
        if not opportunity_id or not seeker_id:
            return {"message": "Не указаны opportunity_id or seeker_id", "success": False}
        opportunity = db.query(Opportunity).filter(Opportunity.id == opportunity_id).first()
        if not opportunity:
            return {"message": "Вакансия не найдена", "success": False}
        seeker = db.query(SeekerProfile).filter(SeekerProfile.id == seeker_id).first()
        if not seeker:
            return {"message": "Соискатель не найден", "success": False}
        favorite = db.query(Favorite).filter(
            Favorite.seeker_id == seeker_id,
            Favorite.opportunity_id == opportunity_id
        ).first()
        if favorite:
            db.delete(favorite)
            db.commit()
            return {"message": "Удалено из избранного", "is_favorite": False, "success": True}
        else:
            favorite = Favorite(
                seeker_id=seeker_id,
                opportunity_id=opportunity_id,
                created_at=datetime.utcnow()
            )
            db.add(favorite)
            db.commit()
            return {"message": "Добавлено в избранное", "is_favorite": True, "success": True}
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        db.rollback()
        return {"message": str(e), "success": False}


@app.post("/api/opportunity/create", response_model=None)
async def create_opportunity(opportunity_data: OpportunityCreate, employer_id: int, db: Session = Depends(get_db)):
    try:
        employer = db.query(EmployerProfile).filter(EmployerProfile.id == employer_id).first()
        if not employer:
            raise HTTPException(status_code=404, detail="Работодатель не найден")
        if employer.verification_status != VerificationStatus.VERIFIED:
            raise HTTPException(status_code=403, detail="Компания не верифицирована")

        latitude, longitude = opportunity_data.latitude, opportunity_data.longitude
        if (not latitude or not longitude) and opportunity_data.location:
            lat, lon = await geocode_address(opportunity_data.location)
            if lat and lon:
                latitude, longitude = lat, lon

        opportunity = Opportunity(
            employer_id=employer_id,
            title=opportunity_data.title,
            description=opportunity_data.description,
            type=opportunity_data.type,
            work_format=opportunity_data.work_format,
            employment_type=opportunity_data.employment_type,
            location=opportunity_data.location,
            latitude=latitude,
            longitude=longitude,
            salary_min=opportunity_data.salary_min,
            salary_max=opportunity_data.salary_max,
            requirements=opportunity_data.requirements,
            tags=json.dumps(opportunity_data.tags) if opportunity_data.tags else "[]",
            contacts=json.dumps(opportunity_data.contacts) if opportunity_data.contacts else "{}",
            expires_at=opportunity_data.expires_at,
            event_date=opportunity_data.event_date,
            is_moderated=False,
            is_active=True
        )

        db.add(opportunity)
        db.commit()
        db.refresh(opportunity)

        return {"message": "Вакансия создана и отправлена на модерацию", "opportunity_id": opportunity.id,
                "success": True}

    except Exception as e:
        db.rollback()
        print(f"❌ Ошибка создания вакансии: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


# ==================== МЕРОПРИЯТИЯ ====================

@app.get("/api/events")
async def get_events(
        request: Request,
        db: Session = Depends(get_db),
        city: Optional[str] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None
):
    """Получение списка мероприятий для главной страницы с количеством участников"""
    query = db.query(Opportunity).filter(
        Opportunity.is_active == True,
        Opportunity.is_moderated == True,
        Opportunity.type == OpportunityType.EVENT
    )
    if city:
        query = query.filter(Opportunity.location.contains(city))
    if date_from:
        try:
            date_from_obj = datetime.strptime(date_from, "%Y-%m-%d")
            query = query.filter(Opportunity.event_date >= date_from_obj)
        except:
            pass
    if date_to:
        try:
            date_to_obj = datetime.strptime(date_to, "%Y-%m-%d")
            query = query.filter(Opportunity.event_date <= date_to_obj)
        except:
            pass

    events = query.order_by(Opportunity.event_date).all()

    current_user = get_current_user(request, db)
    current_user_id = current_user.id if current_user else None

    result = []
    for e in events:
        participants_count = db.query(EventRegistration).filter(
            EventRegistration.event_id == e.id,
            EventRegistration.status == "registered"
        ).count()

        is_registered = False
        if current_user_id:
            registration = db.query(EventRegistration).filter(
                EventRegistration.event_id == e.id,
                EventRegistration.user_id == current_user_id
            ).first()
            is_registered = registration is not None

        result.append({
            "id": e.id,
            "title": e.title,
            "description": e.description,
            "company": e.employer.company_name,
            "location": e.location,
            "latitude": e.latitude,
            "longitude": e.longitude,
            "event_date": e.event_date.isoformat() if e.event_date else None,
            "work_format": e.work_format.value,
            "tags": json.loads(e.tags) if e.tags else [],
            "participants_count": participants_count,
            "is_registered": is_registered
        })

    return result


@app.get("/api/event/participants-count/{event_id}")
async def get_participants_count(
        event_id: int,
        db: Session = Depends(get_db)
):
    """Получение количества участников мероприятия"""
    try:
        count = db.query(EventRegistration).filter(
            EventRegistration.event_id == event_id,
            EventRegistration.status == "registered"
        ).count()
        return {"count": count}
    except Exception as e:
        print(f"Ошибка получения количества участников: {e}")
        return {"count": 0}


@app.get("/api/employer/events/{employer_id}")
async def get_employer_events(
        employer_id: int,
        db: Session = Depends(get_db)
):
    """Получение мероприятий конкретного работодателя с количеством участников"""
    try:
        events = db.query(Opportunity).filter(
            Opportunity.employer_id == employer_id,
            Opportunity.type == OpportunityType.EVENT
        ).order_by(Opportunity.event_date.desc()).all()

        result = []
        for e in events:
            participants_count = db.query(EventRegistration).filter(
                EventRegistration.event_id == e.id,
                EventRegistration.status == "registered"
            ).count()

            result.append({
                "id": e.id,
                "title": e.title,
                "description": e.description or "",
                "location": e.location or "",
                "event_date": e.event_date.isoformat() if e.event_date else None,
                "work_format": e.work_format.value if e.work_format else "OFFICE",
                "is_moderated": e.is_moderated,
                "is_active": e.is_active,
                "participants_count": participants_count
            })
        return result
    except Exception as e:
        print(f"Ошибка в get_employer_events: {e}")
        return []


@app.post("/api/event/register/{event_id}")
async def register_for_event(
        request: Request,
        event_id: int,
        db: Session = Depends(get_db)
):
    """Регистрация соискателя на мероприятие"""
    try:
        current_user = get_current_user(request, db)

        if not current_user:
            return JSONResponse(
                status_code=403,
                content={"detail": "Не авторизован", "success": False}
            )

        if current_user.role != 'seeker':
            return JSONResponse(
                status_code=403,
                content={"detail": "Только соискатели могут регистрироваться", "success": False}
            )

        event = db.query(Opportunity).filter(
            Opportunity.id == event_id,
            Opportunity.type == OpportunityType.EVENT,
            Opportunity.is_active == True,
            Opportunity.is_moderated == True
        ).first()

        if not event:
            return JSONResponse(
                status_code=404,
                content={"detail": "Мероприятие не найдено", "success": False}
            )

        existing = db.query(EventRegistration).filter(
            EventRegistration.event_id == event_id,
            EventRegistration.user_id == current_user.id
        ).first()

        if existing:
            return JSONResponse(
                status_code=400,
                content={"detail": "Вы уже зарегистрированы", "success": False}
            )

        registration = EventRegistration(
            event_id=event_id,
            user_id=current_user.id,
            status="registered",
            registered_at=datetime.utcnow()
        )
        db.add(registration)
        db.commit()

        new_count = db.query(EventRegistration).filter(
            EventRegistration.event_id == event_id,
            EventRegistration.status == "registered"
        ).count()

        return JSONResponse(
            content={
                "message": "Вы успешно зарегистрированы на мероприятие!",
                "success": True,
                "participants_count": new_count
            }
        )

    except Exception as e:
        print(f"❌ Ошибка: {e}")
        db.rollback()
        return JSONResponse(
            status_code=500,
            content={"detail": str(e), "success": False}
        )


@app.post("/api/event/unregister/{event_id}")
async def unregister_from_event(
        request: Request,
        event_id: int,
        db: Session = Depends(get_db)
):
    """Отмена регистрации на мероприятие"""
    current_user = get_current_user(request, db)
    if not current_user:
        raise HTTPException(status_code=403, detail="Не авторизован")

    registration = db.query(EventRegistration).filter(
        EventRegistration.event_id == event_id,
        EventRegistration.user_id == current_user.id
    ).first()

    if not registration:
        raise HTTPException(status_code=404, detail="Вы не зарегистрированы на это мероприятие")

    db.delete(registration)
    db.commit()

    return {"message": "Регистрация отменена", "success": True}


@app.get("/api/event/check-registration/{event_id}")
async def check_registration(
        request: Request,
        event_id: int,
        db: Session = Depends(get_db)
):
    """Проверка, зарегистрирован ли пользователь на мероприятие"""
    current_user = get_current_user(request, db)
    if not current_user:
        return {"is_registered": False}

    registration = db.query(EventRegistration).filter(
        EventRegistration.event_id == event_id,
        EventRegistration.user_id == current_user.id
    ).first()

    return {"is_registered": registration is not None}


@app.get("/api/event/participants/{event_id}")
async def get_event_participants(
        request: Request,
        event_id: int,
        db: Session = Depends(get_db)
):
    """Получение списка участников мероприятия"""
    try:
        print(f"\n🔍 ЗАПРОС СПИСКА УЧАСТНИКОВ мероприятия {event_id}")

        current_user = get_current_user(request, db)
        print(f"   Пользователь: {current_user.id if current_user else 'None'}")

        if not current_user:
            raise HTTPException(status_code=403, detail="Не авторизован")

        event = db.query(Opportunity).filter(Opportunity.id == event_id).first()
        if not event:
            print(f"   ❌ Мероприятие {event_id} не найдено")
            raise HTTPException(status_code=404, detail="Мероприятие не найдено")

        print(f"   Мероприятие: {event.title}")
        print(f"   Организатор ID: {event.employer_id}")

        role_str = get_user_role_safe(current_user)
        is_organizer = (role_str.lower() == 'employer' and
                        event.employer_id == current_user.employer_profile.id)
        is_admin = (role_str.lower() in ['admin', 'curator'])

        print(f"   is_organizer: {is_organizer}")
        print(f"   is_admin: {is_admin}")

        if not (is_organizer or is_admin):
            print(f"   ❌ Доступ запрещен")
            raise HTTPException(status_code=403, detail="Доступ только для организатора мероприятия или администратора")

        registrations = db.query(EventRegistration).filter(
            EventRegistration.event_id == event_id,
            EventRegistration.status == "registered"
        ).all()

        print(f"   Найдено регистраций: {len(registrations)}")

        participants = []
        for reg in registrations:
            user = db.query(User).filter(User.id == reg.user_id).first()
            if user:
                seeker = user.seeker_profile
                participants.append({
                    "user_id": reg.user_id,
                    "username": user.username,
                    "full_name": seeker.full_name if seeker else user.username,
                    "university": seeker.university if seeker else "Не указан",
                    "registered_at": reg.registered_at.strftime('%d.%m.%Y %H:%M') if reg.registered_at else "Неизвестно"
                })

        print(f"✅ Успешно загружено {len(participants)} участников")
        return participants

    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/event/create")
async def create_event(
        request: Request,
        employer_id: int,
        db: Session = Depends(get_db)
):
    """Создание мероприятия работодателем"""
    try:
        event_data = await request.json()

        print("=" * 50)
        print("📥 ПОЛУЧЕНЫ ДАННЫЕ МЕРОПРИЯТИЯ:")
        print(event_data)
        print("=" * 50)

        employer = db.query(EmployerProfile).filter(EmployerProfile.id == employer_id).first()
        if not employer:
            raise HTTPException(status_code=404, detail="Работодатель не найден")

        if employer.verification_status != VerificationStatus.VERIFIED:
            raise HTTPException(status_code=403, detail="Компания не верифицирована")

        title = event_data.get("title", "").strip()
        if not title:
            raise HTTPException(status_code=400, detail="Введите название мероприятия")

        description = event_data.get("description", "").strip()
        if not description:
            raise HTTPException(status_code=400, detail="Введите описание мероприятия")

        is_online = event_data.get("is_online", False)
        print(f"🔍 is_online из запроса: {is_online}")

        location = event_data.get("location", "").strip()
        if not location and not is_online:
            raise HTTPException(status_code=400, detail="Для очного мероприятия укажите место проведения")
        
        if is_online and not location:
            location = "Онлайн"

        event_date_str = event_data.get("event_date", "")
        if not event_date_str:
            raise HTTPException(status_code=400, detail="Укажите дату проведения")

        event_date = None
        try:
            event_date = datetime.strptime(event_date_str, "%Y-%m-%d")
        except:
            raise HTTPException(status_code=400, detail="Неверный формат даты")

        latitude, longitude = None, None
        work_format_value = event_data.get("work_format", "OFFICE")
        try:
            work_format = WorkFormat(work_format_value)
        except:
            work_format = WorkFormat.OFFICE

        if not is_online and work_format in [WorkFormat.OFFICE, WorkFormat.HYBRID] and location and location != "Онлайн":
            lat, lon = await geocode_address(location)
            if lat and lon:
                latitude, longitude = lat, lon

        tags = event_data.get("tags", [])
        if isinstance(tags, str):
            tags = [t.strip() for t in tags.split(',') if t.strip()]

        contacts = event_data.get("contacts", {})
        if isinstance(contacts, str):
            try:
                contacts = json.loads(contacts)
            except:
                contacts = {"email": contacts}

        print(f"✅ СОЗДАЕМ МЕРОПРИЯТИЕ: is_online={is_online}")

        event = Opportunity(
            employer_id=employer_id,
            title=title,
            description=description,
            type=OpportunityType.EVENT,
            work_format=work_format,
            location=location,
            latitude=latitude,
            longitude=longitude,
            event_date=event_date,
            tags=json.dumps(tags),
            contacts=json.dumps(contacts),
            is_moderated=False,
            is_active=True,
            is_online=is_online
        )

        db.add(event)
        db.commit()
        db.refresh(event)

        print(f"✅ Мероприятие создано: ID={event.id}, is_online={event.is_online}")

        return {"message": "Мероприятие создано и отправлено на модерацию", "event_id": event.id, "success": True}

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        print(f"❌ Ошибка создания мероприятия: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/api/event/update/{event_id}")
async def update_event(
        event_id: int,
        event_data: dict,
        employer_id: int,
        db: Session = Depends(get_db)
):
    """Обновление мероприятия"""
    try:
        event = db.query(Opportunity).filter(
            Opportunity.id == event_id,
            Opportunity.employer_id == employer_id,
            Opportunity.type == OpportunityType.EVENT
        ).first()

        if not event:
            raise HTTPException(status_code=404, detail="Мероприятие не найдено")

        if event_data.get("title"):
            event.title = event_data["title"]
        if event_data.get("description"):
            event.description = event_data["description"]
        if event_data.get("location"):
            event.location = event_data["location"]
            lat, lon = await geocode_address(event_data["location"])
            if lat and lon:
                event.latitude, event.longitude = lat, lon
        if event_data.get("event_date"):
            try:
                event.event_date = datetime.strptime(event_data["event_date"], "%Y-%m-%d")
            except:
                pass
        if event_data.get("work_format"):
            try:
                event.work_format = WorkFormat(event_data["work_format"])
            except:
                pass
        if event_data.get("tags"):
            event.tags = json.dumps(event_data["tags"])

        db.commit()
        return {"message": "Мероприятие обновлено", "success": True}

    except Exception as e:
        db.rollback()
        print(f"Ошибка обновления мероприятия: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/event/delete/{event_id}")
async def delete_event(
        event_id: int,
        employer_id: int,
        db: Session = Depends(get_db)
):
    """Удаление мероприятия (soft delete)"""
    try:
        event = db.query(Opportunity).filter(
            Opportunity.id == event_id,
            Opportunity.employer_id == employer_id,
            Opportunity.type == OpportunityType.EVENT
        ).first()

        if not event:
            raise HTTPException(status_code=404, detail="Мероприятие не найдено")

        event.is_active = False
        db.commit()

        return {"message": "Мероприятие удалено", "success": True}

    except Exception as e:
        db.rollback()
        print(f"Ошибка удаления мероприятия: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== МОДЕРАЦИЯ ====================

@app.get("/curator/dashboard", response_class=HTMLResponse)
async def curator_dashboard(request: Request, db: Session = Depends(get_db)):
    try:
        current_user = get_current_user(request, db)

        if not current_user:
            return RedirectResponse(url="/login", status_code=302)

        role_str = current_user.role

        if role_str not in ['curator', 'admin']:
            raise HTTPException(status_code=403, detail="Доступ запрещен. Только для модераторов и администраторов.")

        profile = current_user.curator_profile
        if not profile:
            profile = CuratorProfile(
                user_id=current_user.id,
                university="Администратор платформы",
                position="Главный администратор"
            )
            db.add(profile)
            db.commit()
            db.refresh(profile)

        pending_vacancies = db.query(Opportunity).filter(
            Opportunity.is_moderated == False,
            Opportunity.is_active == True
        ).all()

        pending_employers = db.query(EmployerProfile).filter(
            EmployerProfile.verification_status == VerificationStatus.PENDING
        ).all()

        all_users = db.query(User).all()

        return templates.TemplateResponse("curator_dashboard.html", {
            "request": request,
            "user": current_user,
            "profile": profile,
            "pending_vacancies": pending_vacancies,
            "pending_vacancies_count": len(pending_vacancies),
            "pending_employers": pending_employers,
            "pending_employers_count": len(pending_employers),
            "all_users": all_users,
            "total_users": db.query(User).count(),
            "total_vacancies": db.query(Opportunity).count()
        })

    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Ошибка панели модератора: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/curator/moderate/opportunity", response_model=None)
async def moderate_opportunity(opportunity_id: int, curator_id: int, action: str, comment: str = "",
                               db: Session = Depends(get_db)):
    # Проверяем, что пользователь существует
    curator = db.query(User).filter(User.id == curator_id).first()
    if not curator:
        raise HTTPException(status_code=403, detail="Куратор не найден")

    # Проверяем роль
    role_str = get_user_role_safe(curator)
    if role_str.lower() not in ['curator', 'admin']:
        raise HTTPException(status_code=403, detail="Доступ запрещен. Только для модераторов.")

    # Находим или создаем профиль куратора
    curator_profile = db.query(CuratorProfile).filter(CuratorProfile.user_id == curator_id).first()
    if not curator_profile:
        curator_profile = CuratorProfile(
            user_id=curator_id,
            university="Администратор",
            position="Модератор"
        )
        db.add(curator_profile)
        db.flush()
        print(f"✅ Создан профиль куратора для пользователя {curator_id}")

    # Находим вакансию
    opportunity = db.query(Opportunity).filter(Opportunity.id == opportunity_id).first()
    if not opportunity:
        raise HTTPException(status_code=404, detail="Вакансия не найдена")
    
    # Меняем статус
    if action == "approve":
        opportunity.is_moderated = True
        opportunity.is_active = True
        message = f"Вакансия {opportunity.title} одобрена"
    elif action == "reject":
        opportunity.is_moderated = False
        opportunity.is_active = False
        message = f"Вакансия {opportunity.title} отклонена"
    else:
        raise HTTPException(status_code=400, detail="Неверное действие")
    
    # Создаем лог — используем ID ПРОФИЛЯ куратора
    log = ModerationLog(
        curator_id=curator_profile.id,  # ← ВАЖНО: ID из curator_profiles
        opportunity_id=opportunity_id,
        user_id=None,
        action=f"moderate_opportunity_{action}",
        comment=comment or message
    )
    db.add(log)
    db.commit()
    
    return {"message": message, "success": True}


@app.post("/api/curator/verify-employer", response_model=None)
async def curator_verify_employer(employer_id: int, action: str, curator_id: int, db: Session = Depends(get_db)):
    # Проверяем, что пользователь существует
    curator = db.query(User).filter(User.id == curator_id).first()
    if not curator:
        raise HTTPException(status_code=403, detail="Куратор не найден")

    # Проверяем роль
    role_str = get_user_role_safe(curator)
    if role_str.lower() not in ['curator', 'admin']:
        raise HTTPException(status_code=403, detail="Доступ запрещен. Только для модераторов.")

    # Находим или создаем профиль куратора
    curator_profile = db.query(CuratorProfile).filter(CuratorProfile.user_id == curator_id).first()
    if not curator_profile:
        # Создаем профиль куратора, если его нет
        curator_profile = CuratorProfile(
            user_id=curator_id,
            university="Администратор",
            position="Модератор"
        )
        db.add(curator_profile)
        db.flush()
        print(f"✅ Создан профиль куратора для пользователя {curator_id}")

    # Находим компанию
    employer = db.query(EmployerProfile).filter(EmployerProfile.id == employer_id).first()
    if not employer:
        raise HTTPException(status_code=404, detail="Компания не найдена")
    
    # Обновляем статус
    if action == "verify":
        employer.verification_status = VerificationStatus.VERIFIED
        employer.verified_at = datetime.utcnow()
        message = f"Компания {employer.company_name} верифицирована"
    elif action == "reject":
        employer.verification_status = VerificationStatus.REJECTED
        message = f"Компания {employer.company_name} отклонена"
    else:
        raise HTTPException(status_code=400, detail="Неверное действие")
    
    # Создаем лог - ВАЖНО: используем ID ПРОФИЛЯ куратора, а не ID пользователя
    log = ModerationLog(
        curator_id=curator_profile.id,  # ← ЭТО ГЛАВНОЕ ИСПРАВЛЕНИЕ!
        user_id=employer.user_id,
        action=f"verify_employer_{action}",
        comment=message
    )
    db.add(log)
    db.commit()
    
    return {"message": message, "success": True}

@app.post("/api/curator/toggle-user-status", response_model=None)
async def toggle_user_status(user_id: int, activate: bool, curator_id: int, db: Session = Depends(get_db)):
    curator = db.query(User).filter(User.id == curator_id).first()
    if not curator:
        raise HTTPException(status_code=403, detail="Доступ запрещен")

    role_str = get_user_role_safe(curator)
    if role_str.lower() not in ['curator', 'admin']:
        raise HTTPException(status_code=403, detail="Доступ запрещен. Только для модераторов.")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    user.is_active = activate
    action_text = "разблокирован" if activate else "заблокирован"
    log = ModerationLog(curator_id=curator_id, user_id=user_id,
                        action=f"toggle_user_status_{'activate' if activate else 'block'}",
                        comment=f"Пользователь {user.username} {action_text}")
    db.add(log)
    db.commit()
    return {"message": f"Пользователь {user.username} {action_text}", "success": True}


@app.delete("/api/curator/delete-user", response_model=None)
async def delete_user(user_id: int, curator_id: int, db: Session = Depends(get_db)):
    try:
        # Проверяем права
        curator = db.query(User).filter(User.id == curator_id).first()
        if not curator:
            raise HTTPException(status_code=403, detail="Доступ запрещен")

        role_str = get_user_role_safe(curator)
        if role_str.lower() not in ['curator', 'admin']:
            raise HTTPException(status_code=403, detail="Доступ запрещен. Только для модераторов.")

        # Находим пользователя
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="Пользователь не найден")
        
        username = user.username
        
        # ========== 1. УДАЛЯЕМ СООБЩЕНИЯ ==========
        db.query(Message).filter(
            (Message.sender_id == user.id) | (Message.receiver_id == user.id)
        ).delete(synchronize_session=False)
        
        # ========== 2. УДАЛЯЕМ УВЕДОМЛЕНИЯ ==========
        db.query(Notification).filter(Notification.user_id == user.id).delete(synchronize_session=False)
        
        # ========== 3. УДАЛЯЕМ РЕГИСТРАЦИИ НА МЕРОПРИЯТИЯ ==========
        db.query(EventRegistration).filter(EventRegistration.user_id == user.id).delete(synchronize_session=False)
        
        # ========== 4. УДАЛЯЕМ ДАННЫЕ СОИСКАТЕЛЯ ==========
        if user.seeker_profile:
            seeker_id = user.seeker_profile.id
            
            # Удаляем связи (друзья)
            db.query(Connection).filter(
                (Connection.seeker_id == seeker_id) | 
                (Connection.friend_id == seeker_id)
            ).delete(synchronize_session=False)
            
            # Удаляем отклики
            db.query(ApplicationResponse).filter(
                ApplicationResponse.seeker_id == seeker_id
            ).delete(synchronize_session=False)
            
            # Удаляем избранное
            db.query(Favorite).filter(
                Favorite.seeker_id == seeker_id
            ).delete(synchronize_session=False)
            
            # Удаляем профиль соискателя
            db.delete(user.seeker_profile)
        
        # ========== 5. УДАЛЯЕМ ДАННЫЕ РАБОТОДАТЕЛЯ ==========
        if user.employer_profile:
            employer_id = user.employer_profile.id
            
            # Находим все вакансии работодателя
            opportunities = db.query(Opportunity).filter(
                Opportunity.employer_id == employer_id
            ).all()
            
            for opp in opportunities:
                # Удаляем отклики на эту вакансию
                db.query(ApplicationResponse).filter(
                    ApplicationResponse.opportunity_id == opp.id
                ).delete(synchronize_session=False)
                
                # Удаляем избранное с этой вакансией
                db.query(Favorite).filter(
                    Favorite.opportunity_id == opp.id
                ).delete(synchronize_session=False)
                
                # Удаляем регистрации на это мероприятие
                db.query(EventRegistration).filter(
                    EventRegistration.event_id == opp.id
                ).delete(synchronize_session=False)
                
                # Удаляем саму вакансию
                db.delete(opp)
            
            # Удаляем профиль работодателя
            db.delete(user.employer_profile)
        
        # ========== 6. УДАЛЯЕМ ПРОФИЛЬ КУРАТОРА ==========
        if user.curator_profile:
            # Удаляем логи модерации
            db.query(ModerationLog).filter(
                ModerationLog.curator_id == user.curator_profile.id
            ).delete(synchronize_session=False)
            db.delete(user.curator_profile)
        
        # ========== 7. УДАЛЯЕМ ЛОГИ МОДЕРАЦИИ, ГДЕ USER_ID ==========
        db.query(ModerationLog).filter(
            ModerationLog.user_id == user.id
        ).delete(synchronize_session=False)
        
        # ========== 8. УДАЛЯЕМ САМОГО ПОЛЬЗОВАТЕЛЯ ==========
        db.delete(user)
        
        # Коммитим все изменения
        db.commit()
        
        return {"message": f"Пользователь {username} успешно удален", "success": True}
        
    except Exception as e:
        db.rollback()
        print(f"❌ Ошибка удаления пользователя: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/admin/create-moderator", response_model=None)
async def create_moderator(
        email: str = Form(...),
        username: str = Form(...),
        password: str = Form(...),
        university: str = Form(...),
        position: str = Form(None),
        current_admin_id: int = Form(...),
        db: Session = Depends(get_db)
):
    admin = db.query(User).filter(User.id == current_admin_id, User.role == 'admin').first()
    if not admin:
        raise HTTPException(status_code=403,
                            detail="Доступ запрещен. Только администратор может создавать модераторов.")
    if db.query(User).filter(User.email == email).first():
        raise HTTPException(status_code=400, detail="Email уже зарегистрирован")
    if db.query(User).filter(User.username == username).first():
        raise HTTPException(status_code=400, detail="Имя пользователя уже занято")
    moderator = User(
        email=email,
        username=username,
        password_hash=hash_password(password),
        role='curator',
        is_active=True
    )
    db.add(moderator)
    db.flush()
    profile = CuratorProfile(
        user_id=moderator.id,
        university=university,
        position=position or "Модератор платформы"
    )
    db.add(profile)
    log = ModerationLog(
        curator_id=admin.id,
        user_id=moderator.id,
        action="create_moderator",
        comment=f"Администратор {admin.username} создал модератора {username}"
    )
    db.add(log)
    db.commit()
    return {
        "success": True,
        "message": f"Модератор {username} успешно создан",
        "moderator_id": moderator.id
    }


@app.delete("/api/admin/delete-moderator/{moderator_id}", response_model=None)
async def delete_moderator(moderator_id: int, admin_id: int = Form(...), db: Session = Depends(get_db)):
    admin = db.query(User).filter(User.id == admin_id, User.role == 'admin').first()
    if not admin:
        raise HTTPException(status_code=403, detail="Доступ запрещен")
    moderator = db.query(User).filter(User.id == moderator_id, User.role == 'curator').first()
    if not moderator:
        raise HTTPException(status_code=404, detail="Модератор не найден")
    if moderator.id == admin.id:
        raise HTTPException(status_code=400, detail="Нельзя удалить самого себя")
    db.delete(moderator)
    db.commit()
    return {"message": "Модератор удален", "success": True}


@app.get("/admin/dashboard", response_class=HTMLResponse)
async def admin_dashboard(request: Request, db: Session = Depends(get_db)):
    try:
        current_user = get_current_user(request, db)

        if not current_user:
            return RedirectResponse(url="/login", status_code=302)

        if current_user.role != 'admin':
            raise HTTPException(status_code=403, detail="Доступ запрещен. Только для администратора.")

        admin = current_user

        pending_vacancies = db.query(Opportunity).filter(
            Opportunity.is_moderated == False,
            Opportunity.is_active == True
        ).all()

        pending_employers = db.query(EmployerProfile).filter(
            EmployerProfile.verification_status == VerificationStatus.PENDING
        ).all()

        all_users = db.query(User).all()
        moderators = db.query(User).filter(User.role == 'curator').all()

        return templates.TemplateResponse("admin_dashboard_full.html", {
            "request": request,
            "admin": admin,
            "pending_vacancies": pending_vacancies,
            "pending_vacancies_count": len(pending_vacancies),
            "pending_employers": pending_employers,
            "pending_employers_count": len(pending_employers),
            "all_users": all_users,
            "moderators": moderators,
            "total_users": db.query(User).count(),
            "total_vacancies": db.query(Opportunity).count()
        })

    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Ошибка админ-панели: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


# ==================== ПРОФИЛЬ ====================

@app.post("/api/profile/update", response_model=None)
async def update_profile(
        user_id: int = Form(...),
        full_name: str = Form(None),
        university: str = Form(None),
        course: str = Form(None),
        graduation_year: int = Form(None),
        phone: str = Form(None),
        github: str = Form(None),
        skills: str = Form(None),
        about: str = Form(None),
        db: Session = Depends(get_db)
):
    try:
        profile = db.query(SeekerProfile).filter(SeekerProfile.user_id == user_id).first()
        if not profile:
            raise HTTPException(status_code=404, detail="Профиль не найден")
        if full_name:
            profile.full_name = full_name
        if university:
            profile.university = university
        if course:
            profile.course = course
        if graduation_year:
            profile.graduation_year = graduation_year
        if phone:
            profile.phone = phone
        if github:
            profile.github = github
        if skills:
            try:
                if ',' in skills and not skills.startswith('['):
                    skills_list = [s.strip() for s in skills.split(',') if s.strip()]
                    profile.skills = json.dumps(skills_list, ensure_ascii=False)
                else:
                    profile.skills = skills
            except Exception as e:
                print(f"Ошибка обработки навыков: {e}")
                profile.skills = skills
        if about:
            profile.about = about
        db.commit()
        return {"message": "Профиль обновлен", "success": True}
    except Exception as e:
        print(f"Ошибка обновления профиля: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/profile/privacy")
async def update_privacy(
        request: Request,
        user_id: int = Form(...),
        show_profile: bool = Form(True),
        db: Session = Depends(get_db)
):
    current_user = get_current_user(request, db)
    if not current_user or current_user.id != user_id:
        raise HTTPException(status_code=403, detail="Доступ запрещен")
    profile = db.query(SeekerProfile).filter(SeekerProfile.user_id == user_id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Профиль не найден")
    privacy = json.loads(profile.privacy_settings) if profile.privacy_settings else {"show_profile": True}
    privacy["show_profile"] = show_profile
    profile.privacy_settings = json.dumps(privacy)
    db.commit()
    return {"message": "Настройки сохранены", "show_profile": show_profile, "success": True}


# ==================== ЧАТ ====================

@app.post("/api/chat/send")
async def send_message(
        request: Request,
        receiver_id: int = Form(...),
        opportunity_id: int = Form(None),
        text: str = Form(...),
        db: Session = Depends(get_db)
):
    current_user = get_current_user(request, db)
    if not current_user:
        raise HTTPException(status_code=403, detail="Не авторизован")
    receiver = db.query(User).filter(User.id == receiver_id).first()
    if not receiver:
        raise HTTPException(status_code=404, detail="Получатель не найден")
    message = Message(
        sender_id=current_user.id,
        receiver_id=receiver_id,
        opportunity_id=opportunity_id,
        text=text,
        created_at=datetime.utcnow()
    )
    db.add(message)
    notification = Notification(
        user_id=receiver_id,
        type="new_message",
        title="Новое сообщение",
        message=f"{current_user.username} написал(а) вам: {text[:50]}...",
        created_at=datetime.utcnow()
    )
    db.add(notification)
    db.commit()
    return {"message": "Сообщение отправлено", "success": True}


@app.get("/api/chat/conversations")
async def get_conversations(request: Request, db: Session = Depends(get_db)):
    current_user = get_current_user(request, db)
    if not current_user:
        raise HTTPException(status_code=403, detail="Не авторизован")
    messages = db.query(Message).filter(
        (Message.sender_id == current_user.id) | (Message.receiver_id == current_user.id)
    ).order_by(Message.created_at.desc()).all()
    conversations = {}
    for msg in messages:
        other_id = msg.receiver_id if msg.sender_id == current_user.id else msg.sender_id
        if other_id not in conversations:
            other_user = db.query(User).filter(User.id == other_id).first()
            if other_user:
                unread = db.query(Message).filter(
                    Message.sender_id == other_id,
                    Message.receiver_id == current_user.id,
                    Message.is_read == False
                ).count()
                conversations[other_id] = {
                    "user_id": other_id,
                    "username": other_user.username,
                    "last_message": msg.text[:100],
                    "last_message_time": msg.created_at.strftime('%d.%m.%Y %H:%M'),
                    "unread": unread
                }
    return list(conversations.values())


@app.get("/api/chat/messages/{user_id}")
async def get_messages(request: Request, user_id: int, opportunity_id: Optional[int] = None,
                       db: Session = Depends(get_db)):
    current_user = get_current_user(request, db)
    if not current_user:
        raise HTTPException(status_code=403, detail="Не авторизован")
    query = db.query(Message).filter(
        ((Message.sender_id == current_user.id) & (Message.receiver_id == user_id)) |
        ((Message.sender_id == user_id) & (Message.receiver_id == current_user.id))
    )
    if opportunity_id:
        query = query.filter(Message.opportunity_id == opportunity_id)
    messages = query.order_by(Message.created_at.asc()).all()
    db.query(Message).filter(
        Message.sender_id == user_id,
        Message.receiver_id == current_user.id,
        Message.is_read == False
    ).update({"is_read": True})
    db.commit()
    other_user = db.query(User).filter(User.id == user_id).first()
    return {
        "user": {
            "id": other_user.id,
            "username": other_user.username,
            "role": other_user.role
        },
        "messages": [
            {
                "id": m.id,
                "sender_id": m.sender_id,
                "text": m.text,
                "is_mine": m.sender_id == current_user.id,
                "created_at": m.created_at.strftime('%d.%m.%Y %H:%M')
            }
            for m in messages
        ]
    }


@app.get("/api/chat/unread-count")
async def get_unread_chat_count(request: Request, db: Session = Depends(get_db)):
    current_user = get_current_user(request, db)
    if not current_user:
        return {"count": 0}
    count = db.query(Message).filter(
        Message.receiver_id == current_user.id,
        Message.is_read == False
    ).count()
    return {"count": count}


# ==================== НЕТВОРКИНГ ====================

@app.get("/api/searchers/search")
async def search_seekers(
        request: Request,
        q: Optional[str] = None,
        skills: Optional[str] = None,
        university: Optional[str] = None,
        db: Session = Depends(get_db)
):
    """Поиск других соискателей"""
    try:
        current_user = get_current_user(request, db)

        if not current_user or not current_user.seeker_profile:
            raise HTTPException(status_code=403, detail="Доступ только для соискателей")

        def safe_str(value):
            if value is None:
                return ""
            if isinstance(value, bytes):
                try:
                    return value.decode('utf-8')
                except:
                    try:
                        return value.decode('cp1251')
                    except:
                        return str(value)
            return str(value)

        query = db.query(SeekerProfile).join(User).filter(
            User.role == 'seeker',
            SeekerProfile.id != current_user.seeker_profile.id
        )

        if q and q.strip():
            query = query.filter(SeekerProfile.full_name.contains(q.strip()))

        if university and university.strip():
            query = query.filter(SeekerProfile.university.contains(university.strip()))

        if skills and skills.strip():
            skills_list = [s.strip().lower() for s in skills.split(',') if s.strip()]
            from sqlalchemy import or_
            conditions = []
            for skill in skills_list:
                conditions.append(SeekerProfile.skills.contains(skill))
                conditions.append(SeekerProfile.skills.contains(skill.capitalize()))
            query = query.filter(or_(*conditions))

        seekers = query.all()

        result = []
        for seeker in seekers:
            user = db.query(User).filter(User.id == seeker.user_id).first()

            privacy_settings = safe_str(seeker.privacy_settings)
            try:
                privacy = json.loads(privacy_settings) if privacy_settings else {"show_profile": True}
            except:
                privacy = {"show_profile": True}
            show_profile = privacy.get("show_profile", True)

            connection = db.query(Connection).filter(
                ((Connection.seeker_id == current_user.seeker_profile.id) & (Connection.friend_id == seeker.id)) |
                ((Connection.seeker_id == seeker.id) & (Connection.friend_id == current_user.seeker_profile.id))
            ).first()

            connection_status = None
            if connection:
                if connection.status == "pending":
                    if connection.seeker_id == current_user.seeker_profile.id:
                        connection_status = "request_sent"
                    else:
                        connection_status = "request_received"
                elif connection.status == "accepted":
                    connection_status = "friends"

            skills_list = []
            skills_str = safe_str(seeker.skills)
            if skills_str:
                try:
                    skills_list = json.loads(skills_str)
                except:
                    skills_list = [s.strip() for s in skills_str.split(',') if s.strip()]

            result.append({
                "id": seeker.id,
                "user_id": seeker.user_id,
                "username": safe_str(user.username) if user else "",
                "full_name": safe_str(seeker.full_name) or (safe_str(user.username) if user else "Без имени"),
                "university": safe_str(seeker.university) if show_profile else "Профиль скрыт",
                "course": safe_str(seeker.course),
                "about": safe_str(seeker.about)[:200] if seeker.about and show_profile else "",
                "skills": skills_list if show_profile else [],
                "github": safe_str(seeker.github) if show_profile else None,
                "connection_status": connection_status,
                "profile_hidden": not show_profile
            })

        return result

    except Exception as e:
        print(f"❌ Ошибка в search_seekers: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/connection/request")
async def send_connection_request(request: Request, friend_id: int, db: Session = Depends(get_db)):
    current_user = get_current_user(request, db)
    if not current_user or not current_user.seeker_profile:
        raise HTTPException(status_code=403, detail="Только соискатели могут отправлять запросы")
    friend = db.query(SeekerProfile).filter(SeekerProfile.id == friend_id).first()
    if not friend:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    existing = db.query(Connection).filter(
        ((Connection.seeker_id == current_user.seeker_profile.id) & (Connection.friend_id == friend_id)) |
        ((Connection.seeker_id == friend_id) & (Connection.friend_id == current_user.seeker_profile.id))
    ).first()
    if existing:
        if existing.status == "pending":
            raise HTTPException(status_code=400, detail="Запрос уже отправлен")
        elif existing.status == "accepted":
            raise HTTPException(status_code=400, detail="Вы уже в контактах")
    connection = Connection(
        seeker_id=current_user.seeker_profile.id,
        friend_id=friend_id,
        status="pending",
        created_at=datetime.utcnow()
    )
    db.add(connection)
    notification = Notification(
        user_id=friend.user_id,
        type="connection_request",
        title="Новый запрос в контакты",
        message=f"{current_user.seeker_profile.full_name or current_user.username} хочет добавить вас в контакты",
        data=json.dumps({"seeker_id": current_user.seeker_profile.id, "name": current_user.seeker_profile.full_name}),
        created_at=datetime.utcnow()
    )
    db.add(notification)
    db.commit()
    return {"message": "Запрос отправлен", "success": True}


@app.post("/api/connection/accept/{connection_id}")
async def accept_connection_request(request: Request, connection_id: int, db: Session = Depends(get_db)):
    """Принять запрос на добавление в контакты"""
    try:
        current_user = get_current_user(request, db)

        print(f"\n🔍 ПРИНЯТИЕ ЗАПРОСА ID={connection_id}")
        print(f"   current_user: {current_user.id if current_user else 'None'}")

        if not current_user or not current_user.seeker_profile:
            raise HTTPException(status_code=403, detail="Только соискатели могут принимать запросы")

        connection = db.query(Connection).filter(Connection.id == connection_id).first()
        if not connection:
            print(f"   ❌ Запрос {connection_id} не найден")
            raise HTTPException(status_code=404, detail="Запрос не найден")

        print(
            f"   connection: seeker_id={connection.seeker_id}, friend_id={connection.friend_id}, status={connection.status}")

        # Проверяем, что запрос адресован текущему пользователю
        if connection.friend_id != current_user.seeker_profile.id:
            print(
                f"   ❌ Это не ваш запрос (friend_id={connection.friend_id}, current={current_user.seeker_profile.id})")
            raise HTTPException(status_code=403, detail="Это не ваш запрос")

        if connection.status != "pending":
            print(f"   ❌ Запрос уже обработан (status={connection.status})")
            raise HTTPException(status_code=400, detail="Запрос уже обработан")

        connection.status = "accepted"
        print(f"   ✅ Статус изменён на accepted")

        # Уведомляем отправителя
        sender = db.query(SeekerProfile).filter(SeekerProfile.id == connection.seeker_id).first()
        if sender:
            notification = Notification(
                user_id=sender.user_id,
                type="connection_accepted",
                title="Запрос принят",
                message=f"{current_user.seeker_profile.full_name or current_user.username} принял(а) ваш запрос в контакты",
                created_at=datetime.utcnow()
            )
            db.add(notification)
            print(f"   ✅ Уведомление отправлено пользователю {sender.user_id}")

        db.commit()
        print(f"✅ Запрос принят!")
        return {"message": "Запрос принят", "success": True}

    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/connection/reject/{connection_id}")
async def reject_connection_request(request: Request, connection_id: int, db: Session = Depends(get_db)):
    current_user = get_current_user(request, db)
    if not current_user or not current_user.seeker_profile:
        raise HTTPException(status_code=403, detail="Только соискатели могут отклонять запросы")
    connection = db.query(Connection).filter(Connection.id == connection_id).first()
    if not connection:
        raise HTTPException(status_code=404, detail="Запрос не найден")
    if connection.friend_id != current_user.seeker_profile.id:
        raise HTTPException(status_code=403, detail="Это не ваш запрос")
    if connection.status != "pending":
        raise HTTPException(status_code=400, detail="Запрос уже обработан")
    db.delete(connection)
    db.commit()
    return {"message": "Запрос отклонен", "success": True}


@app.get("/api/connections")
async def get_my_connections(request: Request, status: Optional[str] = "accepted", db: Session = Depends(get_db)):
    """Получение контактов или запросов"""
    try:
        current_user = get_current_user(request, db)
        if not current_user or not current_user.seeker_profile:
            raise HTTPException(status_code=403, detail="Доступ только для соискателей")

        print(f"\n🔍 ПОЛУЧЕНИЕ КОНТАКТОВ, status={status}")
        print(f"   current_user.seeker_profile.id = {current_user.seeker_profile.id}")

        if status == "pending":
            # Входящие запросы (кто хочет добавить меня)
            connections = db.query(Connection).filter(
                Connection.friend_id == current_user.seeker_profile.id,
                Connection.status == "pending"
            ).all()

            print(f"   Найдено входящих запросов: {len(connections)}")

            result = []
            for conn in connections:
                sender = db.query(SeekerProfile).filter(SeekerProfile.id == conn.seeker_id).first()
                if sender:
                    user = db.query(User).filter(User.id == sender.user_id).first()
                    result.append({
                        "id": conn.id,
                        "seeker_id": sender.id,
                        "user_id": sender.user_id,
                        "name": sender.full_name or (user.username if user else "Пользователь"),
                        "university": sender.university,
                        "skills": json.loads(sender.skills) if sender.skills else [],
                        "created_at": conn.created_at.strftime('%d.%m.%Y %H:%M')
                    })
                    print(f"   - Запрос ID={conn.id} от {sender.full_name}")
            return result

        else:
            # Мои контакты (принятые связи)
            connections = db.query(Connection).filter(
                ((Connection.seeker_id == current_user.seeker_profile.id) | (
                        Connection.friend_id == current_user.seeker_profile.id)),
                Connection.status == "accepted"
            ).all()

            result = []
            for conn in connections:
                friend_id = conn.seeker_id if conn.friend_id == current_user.seeker_profile.id else conn.friend_id
                friend = db.query(SeekerProfile).filter(SeekerProfile.id == friend_id).first()
                if friend:
                    user = db.query(User).filter(User.id == friend.user_id).first()
                    privacy = json.loads(friend.privacy_settings) if friend.privacy_settings else {"show_profile": True}
                    show_profile = privacy.get("show_profile", True)
                    result.append({
                        "id": conn.id,
                        "friend_id": friend.id,
                        "user_id": friend.user_id,
                        "name": friend.full_name or (user.username if user else "Пользователь"),
                        "university": friend.university if show_profile else "Скрыто",
                        "skills": json.loads(friend.skills) if friend.skills and show_profile else [],
                        "about": friend.about[:200] if friend.about and show_profile else "",
                        "github": friend.github if show_profile else None,
                        "privacy_hidden": not show_profile
                    })
            return result

    except Exception as e:
        print(f"❌ Ошибка в get_my_connections: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/event/{event_id}", response_class=HTMLResponse)
async def event_detail(request: Request, event_id: int, db: Session = Depends(get_db)):
    """Страница детального просмотра мероприятия"""
    try:
        event = db.query(Opportunity).filter(
            Opportunity.id == event_id,
            Opportunity.type == OpportunityType.EVENT,
            Opportunity.is_active == True,
            Opportunity.is_moderated == True
        ).first()

        if not event:
            raise HTTPException(status_code=404, detail="Мероприятие не найдено")

        event.views += 1
        db.commit()

        current_user = get_current_user(request, db)

        # Получаем количество участников
        participants_count = db.query(EventRegistration).filter(
            EventRegistration.event_id == event_id,
            EventRegistration.status == "registered"
        ).count()

        # Проверяем, зарегистрирован ли текущий пользователь
        is_registered = False
        if current_user:
            registration = db.query(EventRegistration).filter(
                EventRegistration.event_id == event_id,
                EventRegistration.user_id == current_user.id
            ).first()
            is_registered = registration is not None

        # Получаем список участников (только для организатора)
        participants = []
        if current_user:
            role_str = get_user_role_safe(current_user)
            if role_str.lower() == 'employer' and current_user.employer_profile.id == event.employer_id:
                registrations = db.query(EventRegistration).filter(
                    EventRegistration.event_id == event_id,
                    EventRegistration.status == "registered"
                ).all()
                for reg in registrations:
                    user = db.query(User).filter(User.id == reg.user_id).first()
                    if user:
                        seeker = user.seeker_profile
                        participants.append({
                            "full_name": seeker.full_name if seeker else user.username,
                            "university": seeker.university if seeker else "Не указан",
                            "registered_at": reg.registered_at.strftime('%d.%m.%Y %H:%M')
                        })

        return templates.TemplateResponse("event_detail.html", {
            "request": request,
            "event": event,
            "tags": json.loads(event.tags) if event.tags else [],
            "contacts": json.loads(event.contacts) if event.contacts else {},
            "current_user": current_user,
            "participants_count": participants_count,
            "is_registered": is_registered,
            "participants": participants
        })

    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Ошибка загрузки мероприятия: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/connection/remove/{friend_id}")
async def remove_connection(request: Request, friend_id: int, db: Session = Depends(get_db)):
    current_user = get_current_user(request, db)
    if not current_user or not current_user.seeker_profile:
        raise HTTPException(status_code=403, detail="Доступ только для соискателей")
    connection = db.query(Connection).filter(
        ((Connection.seeker_id == current_user.seeker_profile.id) & (Connection.friend_id == friend_id)) |
        ((Connection.seeker_id == friend_id) & (Connection.friend_id == current_user.seeker_profile.id)),
        Connection.status == "accepted"
    ).first()
    if not connection:
        raise HTTPException(status_code=404, detail="Контакт не найден")
    db.delete(connection)
    db.commit()
    return {"message": "Контакт удален", "success": True}


# ==================== УВЕДОМЛЕНИЯ ====================

@app.get("/api/notifications")
async def get_notifications(request: Request, unread_only: bool = False, db: Session = Depends(get_db)):
    current_user = get_current_user(request, db)
    if not current_user:
        raise HTTPException(status_code=403, detail="Не авторизован")
    query = db.query(Notification).filter(Notification.user_id == current_user.id)
    if unread_only:
        query = query.filter(Notification.is_read == False)
    notifications = query.order_by(Notification.created_at.desc()).limit(50).all()
    return [
        {
            "id": n.id,
            "type": n.type,
            "title": n.title,
            "message": n.message,
            "data": json.loads(n.data) if n.data else {},
            "is_read": n.is_read,
            "created_at": n.created_at.strftime('%d.%m.%Y %H:%M')
        }
        for n in notifications
    ]


@app.post("/api/notifications/mark-read/{notification_id}")
async def mark_notification_read(request: Request, notification_id: int, db: Session = Depends(get_db)):
    current_user = get_current_user(request, db)
    if not current_user:
        raise HTTPException(status_code=403, detail="Не авторизован")
    notification = db.query(Notification).filter(
        Notification.id == notification_id,
        Notification.user_id == current_user.id
    ).first()
    if not notification:
        raise HTTPException(status_code=404, detail="Уведомление не найдено")
    notification.is_read = True
    db.commit()
    return {"success": True}


@app.post("/api/notifications/mark-all-read")
async def mark_all_notifications_read(request: Request, db: Session = Depends(get_db)):
    current_user = get_current_user(request, db)
    if not current_user:
        raise HTTPException(status_code=403, detail="Не авторизован")
    db.query(Notification).filter(
        Notification.user_id == current_user.id,
        Notification.is_read == False
    ).update({"is_read": True})
    db.commit()
    return {"success": True}


@app.get("/api/notifications/unread-count")
async def get_unread_count(request: Request, db: Session = Depends(get_db)):
    current_user = get_current_user(request, db)
    if not current_user:
        return {"count": 0}
    count = db.query(Notification).filter(
        Notification.user_id == current_user.id,
        Notification.is_read == False
    ).count()
    return {"count": count}


# ==================== ВЫХОД ====================

@app.get("/logout")
async def logout(request: Request, response: Response, db: Session = Depends(get_db)):
    session_token = request.cookies.get("session_token")
    if session_token and session_token in sessions:
        del sessions[session_token]
    response.delete_cookie("session_token")
    return RedirectResponse(url="/", status_code=302)


# ==================== ТЕСТОВЫЕ ПОЛЬЗОВАТЕЛИ ====================

@app.get("/check-users")
async def check_users(db: Session = Depends(get_db)):
    users = db.query(User).all()
    result = []
    for user in users:
        user_data = {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "role": user.role,
            "is_active": user.is_active
        }
        if user.role == 'employer' and user.employer_profile:
            user_data["verification_status"] = user.employer_profile.verification_status.value
        result.append(user_data)
    return result


@app.get("/create-test-user")
async def create_test_user(db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.username == "testuser").first()
    if existing:
        profile = existing.seeker_profile
        if not profile:
            profile = SeekerProfile(
                user_id=existing.id,
                full_name=existing.username,
                university="Тестовый Университет",
                course="3 курс",
                about="Это тестовый пользователь"
            )
            db.add(profile)
            db.commit()
            return {"message": "Профиль создан для существующего пользователя", "username": existing.username,
                    "password": "123456"}
        return {"message": "Тестовый пользователь уже существует", "username": existing.username}
    user = User(
        email="test@test.ru",
        username="testuser",
        password_hash=hash_password("123456"),
        role='seeker',
        is_active=True
    )
    db.add(user)
    db.flush()
    profile = SeekerProfile(
        user_id=user.id,
        full_name="Тестовый Пользователь",
        university="Тестовый Университет",
        course="3 курс",
        about="Это тестовый пользователь для проверки функционала"
    )
    db.add(profile)
    db.commit()
    return {
        "message": "Тестовый пользователь создан",
        "username": "testuser",
        "password": "123456",
        "user_id": user.id
    }


@app.get("/create-test-employer")
async def create_test_employer(db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.username == "testemployer").first()
    if existing:
        db.delete(existing)
        db.commit()
    employer_user = User(
        email="employer@test.ru",
        username="testemployer",
        password_hash=hash_password("employer123"),
        role='employer',
        is_active=True
    )
    db.add(employer_user)
    db.commit()
    db.refresh(employer_user)
    profile = EmployerProfile(
        user_id=employer_user.id,
        company_name="Тестовая IT Компания",
        description="Мы разрабатываем инновационные решения в области искусственного интеллекта и машинного обучения.",
        industry="Информационные технологии",
        website="https://testcompany.ru",
        address="ул. Тестовая, д. 1",
        city="Москва",
        inn="1234567890",
        verification_status=VerificationStatus.VERIFIED,
        verified_at=datetime.utcnow()
    )
    db.add(profile)
    db.commit()
    return {
        "message": "Тестовый работодатель создан (верифицирован)",
        "username": "testemployer",
        "password": "employer123",
        "company": "Тестовая IT Компания",
        "verification_status": "VERIFIED"
    }


@app.get("/create-test-curator")
async def create_test_curator(db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.username == "testcurator").first()
    if existing:
        return {"message": "Тестовый куратор уже существует", "username": existing.username}
    curator_user = User(
        email="curator@test.ru",
        username="testcurator",
        password_hash=hash_password("curator123"),
        role='curator',
        is_active=True
    )
    db.add(curator_user)
    db.commit()
    db.refresh(curator_user)
    profile = CuratorProfile(
        user_id=curator_user.id,
        university="МГУ им. Ломоносова",
        position="Старший модератор"
    )
    db.add(profile)
    db.commit()
    return {
        "message": "Тестовый куратор создан",
        "username": "testcurator",
        "password": "curator123"
    }


@app.get("/verify-employer/{user_id}")
async def verify_employer(user_id: int, db: Session = Depends(get_db)):
    profile = db.query(EmployerProfile).filter(EmployerProfile.user_id == user_id).first()
    if profile:
        profile.verification_status = VerificationStatus.VERIFIED
        profile.verified_at = datetime.utcnow()
        db.commit()
        return {"message": f"Компания {profile.company_name} верифицирована"}
    return {"message": "Работодатель не найден"}


# ==================== ИНИЦИАЛИЗАЦИЯ ====================

def init_admin():
    db = SessionLocal()
    admin = db.query(User).filter(User.role == 'admin').first()
    if not admin:
        admin = User(
            email="admin@tramplin.ru",
            username="admin",
            password_hash=hash_password("admin123"),
            role="admin",
            is_active=True
        )
        db.add(admin)
        db.flush()
        curator = CuratorProfile(
            user_id=admin.id,
            university="Администратор платформы",
            position="Главный администратор"
        )
        db.add(curator)

        system_tags = [
            {"name": "Python", "category": "technology", "is_system": True},
            {"name": "Java", "category": "technology", "is_system": True},
            {"name": "JavaScript", "category": "technology", "is_system": True},
            {"name": "C++", "category": "technology", "is_system": True},
            {"name": "SQL", "category": "technology", "is_system": True},
            {"name": "React", "category": "technology", "is_system": True},
            {"name": "Junior", "category": "level", "is_system": True},
            {"name": "Middle", "category": "level", "is_system": True},
            {"name": "Senior", "category": "level", "is_system": True},
            {"name": "Стажировка", "category": "type", "is_system": True}
        ]
        for tag_data in system_tags:
            tag = Tag(**tag_data)
            db.add(tag)
        db.commit()
    db.close()


@app.on_event("startup")
async def startup_event():
    init_admin()



# ==================== МОДЕРАТОР: РЕДАКТИРОВАНИЕ ВАКАНСИЙ ====================

@app.put("/api/curator/opportunity/{opportunity_id}")
async def curator_update_opportunity(
    opportunity_id: int,
    opportunity_data: dict,
    request: Request,
    db: Session = Depends(get_db)
):
    """Модератор редактирует вакансию"""
    try:
        current_user = get_current_user(request, db)
        
        if not current_user:
            raise HTTPException(status_code=403, detail="Не авторизован")
        
        role_str = get_user_role_safe(current_user)
        if role_str.lower() not in ['curator', 'admin']:
            raise HTTPException(status_code=403, detail="Доступ только для модераторов")
        
        opportunity = db.query(Opportunity).filter(Opportunity.id == opportunity_id).first()
        if not opportunity:
            raise HTTPException(status_code=404, detail="Вакансия не найдена")
        
        # Обновляем поля
        if "title" in opportunity_data:
            opportunity.title = opportunity_data["title"]
        if "description" in opportunity_data:
            opportunity.description = opportunity_data["description"]
        if "type" in opportunity_data:
            try:
                if opportunity_data["type"] == "Вакансия":
                    opportunity.type = OpportunityType.VACANCY
                elif opportunity_data["type"] == "Стажировка":
                    opportunity.type = OpportunityType.INTERNSHIP
                elif opportunity_data["type"] == "Менторская программа":
                    opportunity.type = OpportunityType.MENTORING
            except:
                pass
        if "work_format" in opportunity_data:
            try:
                if opportunity_data["work_format"] == "В офисе":
                    opportunity.work_format = WorkFormat.OFFICE
                elif opportunity_data["work_format"] == "Удаленно":
                    opportunity.work_format = WorkFormat.REMOTE
                elif opportunity_data["work_format"] == "Гибрид":
                    opportunity.work_format = WorkFormat.HYBRID
            except:
                pass
        if "location" in opportunity_data:
            opportunity.location = opportunity_data["location"]
        if "salary_min" in opportunity_data:
            opportunity.salary_min = opportunity_data["salary_min"]
        if "salary_max" in opportunity_data:
            opportunity.salary_max = opportunity_data["salary_max"]
        if "requirements" in opportunity_data:
            opportunity.requirements = opportunity_data["requirements"]
        if "tags" in opportunity_data:
            if isinstance(opportunity_data["tags"], list):
                opportunity.tags = json.dumps(opportunity_data["tags"])
            elif isinstance(opportunity_data["tags"], str):
                tags_list = [t.strip() for t in opportunity_data["tags"].split(',') if t.strip()]
                opportunity.tags = json.dumps(tags_list)
        if "is_moderated" in opportunity_data:
            opportunity.is_moderated = opportunity_data["is_moderated"] == "true" or opportunity_data["is_moderated"] == True
        if "is_active" in opportunity_data:
            opportunity.is_active = opportunity_data["is_active"] == "true" or opportunity_data["is_active"] == True
        
        db.commit()
        
        return {"message": "Вакансия обновлена", "success": True}
        
    except Exception as e:
        db.rollback()
        print(f"❌ Ошибка: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/api/curator/event/{event_id}")
async def curator_update_event(
    event_id: int,
    event_data: dict,
    request: Request,
    db: Session = Depends(get_db)
):
    """Модератор редактирует мероприятие"""
    try:
        current_user = get_current_user(request, db)
        
        if not current_user:
            raise HTTPException(status_code=403, detail="Не авторизован")
        
        role_str = get_user_role_safe(current_user)
        if role_str.lower() not in ['curator', 'admin']:
            raise HTTPException(status_code=403, detail="Доступ только для модераторов")
        
        event = db.query(Opportunity).filter(
            Opportunity.id == event_id,
            Opportunity.type == OpportunityType.EVENT
        ).first()
        
        if not event:
            raise HTTPException(status_code=404, detail="Мероприятие не найдено")
        
        # Обновляем поля
        if "title" in event_data:
            event.title = event_data["title"]
        if "description" in event_data:
            event.description = event_data["description"]
        if "location" in event_data:
            event.location = event_data["location"]
        if "event_date" in event_data:
            try:
                event.event_date = datetime.strptime(event_data["event_date"], "%Y-%m-%d")
            except:
                pass
        if "is_online" in event_data:
            event.is_online = event_data["is_online"] == "1" or event_data["is_online"] == 1 or event_data["is_online"] == True
        if "tags" in event_data:
            if isinstance(event_data["tags"], list):
                event.tags = json.dumps(event_data["tags"])
            elif isinstance(event_data["tags"], str):
                tags_list = [t.strip() for t in event_data["tags"].split(',') if t.strip()]
                event.tags = json.dumps(tags_list)
        if "contacts" in event_data:
            if isinstance(event_data["contacts"], dict):
                event.contacts = json.dumps(event_data["contacts"])
            elif isinstance(event_data["contacts"], str):
                event.contacts = json.dumps({"email": event_data["contacts"]})
        if "is_moderated" in event_data:
            event.is_moderated = event_data["is_moderated"] == "true" or event_data["is_moderated"] == True
        if "is_active" in event_data:
            event.is_active = event_data["is_active"] == "true" or event_data["is_active"] == True
        
        db.commit()
        
        return {"message": "Мероприятие обновлено", "success": True}
        
    except Exception as e:
        db.rollback()
        print(f"❌ Ошибка: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/curator/opportunities")
async def curator_get_all_opportunities(
    request: Request,
    db: Session = Depends(get_db),
    type_filter: Optional[str] = None,
    status_filter: Optional[str] = None
):
    """Модератор получает все вакансии и мероприятия"""
    try:
        current_user = get_current_user(request, db)
        
        if not current_user:
            raise HTTPException(status_code=403, detail="Не авторизован")
        
        role_str = get_user_role_safe(current_user)
        if role_str.lower() not in ['curator', 'admin']:
            raise HTTPException(status_code=403, detail="Доступ только для модераторов")
        
        query = db.query(Opportunity)
        
        if type_filter:
            if type_filter == "vacancy":
                query = query.filter(Opportunity.type != OpportunityType.EVENT)
            elif type_filter == "event":
                query = query.filter(Opportunity.type == OpportunityType.EVENT)
        
        if status_filter:
            if status_filter == "pending":
                query = query.filter(Opportunity.is_moderated == False)
            elif status_filter == "approved":
                query = query.filter(Opportunity.is_moderated == True, Opportunity.is_active == True)
            elif status_filter == "rejected":
                query = query.filter(Opportunity.is_moderated == False, Opportunity.is_active == False)
        
        opportunities = query.order_by(Opportunity.published_at.desc()).all()
        
        result = []
        for opp in opportunities:
            result.append({
                "id": opp.id,
                "title": opp.title,
                "description": opp.description,
                "type": opp.type.value,
                "work_format": opp.work_format.value,
                "location": opp.location,
                "latitude": opp.latitude,
                "longitude": opp.longitude,
                "salary_min": opp.salary_min,
                "salary_max": opp.salary_max,
                "requirements": opp.requirements,
                "tags": json.loads(opp.tags) if opp.tags else [],
                "contacts": json.loads(opp.contacts) if opp.contacts else {},
                "employer_name": opp.employer.company_name if opp.employer else "Неизвестно",
                "employer_id": opp.employer_id,
                "is_moderated": opp.is_moderated,
                "is_active": opp.is_active,
                "is_event": opp.type == OpportunityType.EVENT,
                "event_date": opp.event_date.strftime('%Y-%m-%d') if opp.event_date else None,
                "is_online": getattr(opp, 'is_online', False),
                "published_at": opp.published_at.strftime('%d.%m.%Y %H:%M')
            })
        
        return result
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        raise HTTPException(status_code=500, detail=str(e))



if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)