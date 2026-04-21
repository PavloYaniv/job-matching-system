from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.orm import Session, joinedload

import models
import schemas
from database import Base, SessionLocal, engine
from matching import calculate_match_percent

app = FastAPI(title="Information System for Employment Support")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = Path(__file__).resolve().parent
app.mount("/static", StaticFiles(directory=BASE_DIR), name="static")

LEVEL_ORDER = ["trainee", "junior", "middle", "lead"]


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def ensure_schema_updates() -> None:
    with engine.connect() as connection:
        candidate_columns = {
            row[1] for row in connection.execute(text("PRAGMA table_info(candidates)")).fetchall()
        }
        vacancy_columns = {
            row[1] for row in connection.execute(text("PRAGMA table_info(vacancies)")).fetchall()
        }

        if "level" not in candidate_columns:
            connection.execute(
                text("ALTER TABLE candidates ADD COLUMN level VARCHAR(50) NOT NULL DEFAULT 'junior'")
            )
        if "desired_position" not in candidate_columns:
            connection.execute(
                text(
                    "ALTER TABLE candidates ADD COLUMN desired_position "
                    "VARCHAR(255) NOT NULL DEFAULT 'Junior Developer'"
                )
            )
        if "level" not in vacancy_columns:
            connection.execute(
                text("ALTER TABLE vacancies ADD COLUMN level VARCHAR(50) NOT NULL DEFAULT 'junior'")
            )
        if "specialization" not in vacancy_columns:
            connection.execute(
                text(
                    "ALTER TABLE vacancies ADD COLUMN specialization "
                    "VARCHAR(255) NOT NULL DEFAULT 'Software Development'"
                )
            )
        connection.commit()


def normalize_level(value: str) -> str:
    normalized = value.strip().lower()
    if normalized not in LEVEL_ORDER:
        raise HTTPException(
            status_code=400,
            detail="Invalid level. Allowed: trainee, junior, middle, lead",
        )
    return normalized


def matches_level_filter(candidate_level: str, vacancy_level: str, plus_minus: bool) -> bool:
    if not plus_minus:
        return candidate_level == vacancy_level
    try:
        c_idx = LEVEL_ORDER.index(candidate_level)
        v_idx = LEVEL_ORDER.index(vacancy_level)
    except ValueError:
        return candidate_level == vacancy_level
    return abs(c_idx - v_idx) <= 1


def tokenize(value: str) -> set[str]:
    return {token.strip().lower() for token in value.replace("-", " ").split() if token.strip()}


def matches_specialization_filter(desired_position: str, vacancy_specialization: str, plus_minus: bool) -> bool:
    desired = desired_position.strip().lower()
    specialization = vacancy_specialization.strip().lower()
    if not desired or not specialization:
        return True
    if not plus_minus:
        return desired == specialization
    return bool(tokenize(desired).intersection(tokenize(specialization)))


def seed_data(db: Session) -> None:
    if db.query(models.Skill).count() > 0:
        return

    skills_map = {
        name: models.Skill(name=name)
        for name in [
            "Python",
            "SQL",
            "FastAPI",
            "JavaScript",
            "HTML",
            "CSS",
            "Git",
            "Testing",
            "Docker",
            "Communication",
        ]
    }
    db.add_all(skills_map.values())
    db.flush()

    candidates = [
        models.Candidate(
            full_name="Анна Коваль",
            university="КНУ",
            specialty="Комп'ютерні науки",
            level="junior",
            desired_position="developer",
            skills=[
                skills_map["Python"],
                skills_map["SQL"],
                skills_map["FastAPI"],
                skills_map["Git"],
                skills_map["Communication"],
            ],
        ),
        models.Candidate(
            full_name="Ігор Мельник",
            university="ЛПНУ",
            specialty="Інженерія програмного забезпечення",
            level="trainee",
            desired_position="designer",
            skills=[
                skills_map["JavaScript"],
                skills_map["HTML"],
                skills_map["CSS"],
                skills_map["Git"],
                skills_map["Testing"],
            ],
        ),
    ]

    vacancies = [
        models.Vacancy(
            title="Junior Backend Developer",
            company="DataBridge",
            level="junior",
            specialization="developer",
            description="Розробка API для внутрішніх сервісів.",
            required_skills=[
                skills_map["Python"],
                skills_map["SQL"],
                skills_map["FastAPI"],
                skills_map["Git"],
            ],
        ),
        models.Vacancy(
            title="Junior Frontend Developer",
            company="WebLine",
            level="trainee",
            specialization="designer",
            description="Розробка клієнтської частини вебзастосунків.",
            required_skills=[
                skills_map["JavaScript"],
                skills_map["HTML"],
                skills_map["CSS"],
                skills_map["Git"],
            ],
        ),
        models.Vacancy(
            title="QA Intern",
            company="QualityFirst",
            level="trainee",
            specialization="analyst",
            description="Тестування та документування дефектів.",
            required_skills=[
                skills_map["Testing"],
                skills_map["Communication"],
                skills_map["SQL"],
            ],
        ),
    ]

    db.add_all(candidates + vacancies)
    db.commit()


@app.on_event("startup")
def on_startup() -> None:
    Base.metadata.create_all(bind=engine)
    ensure_schema_updates()
    db = SessionLocal()
    try:
        seed_data(db)
    finally:
        db.close()


@app.get("/api/candidates", response_model=list[schemas.CandidateBase])
def get_candidates(db: Session = Depends(get_db)):
    return db.query(models.Candidate).order_by(models.Candidate.id.asc()).all()


@app.get("/api/skills", response_model=list[schemas.SkillBase])
def get_skills(db: Session = Depends(get_db)):
    return db.query(models.Skill).order_by(models.Skill.name.asc()).all()


@app.post("/api/candidates", response_model=schemas.CandidateCreatedResponse, status_code=201)
def create_candidate(payload: schemas.CandidateCreate, db: Session = Depends(get_db)):
    normalized_level = normalize_level(payload.level)
    normalized_skill_names = sorted({name.strip() for name in payload.skills if name.strip()})
    if not normalized_skill_names:
        raise HTTPException(status_code=400, detail="At least one skill is required")

    existing_skills = (
        db.query(models.Skill)
        .filter(models.Skill.name.in_(normalized_skill_names))
        .all()
    )
    skill_map = {skill.name: skill for skill in existing_skills}

    for skill_name in normalized_skill_names:
        if skill_name not in skill_map:
            new_skill = models.Skill(name=skill_name)
            db.add(new_skill)
            db.flush()
            skill_map[skill_name] = new_skill

    candidate = models.Candidate(
        full_name=payload.full_name.strip(),
        university="Не вказано",
        specialty="Не вказано",
        level=normalized_level,
        desired_position=payload.desired_position.strip().lower(),
        skills=[skill_map[name] for name in normalized_skill_names],
    )
    db.add(candidate)
    db.commit()
    db.refresh(candidate)

    return schemas.CandidateCreatedResponse(
        id=candidate.id,
        full_name=candidate.full_name,
        level=candidate.level,
        desired_position=candidate.desired_position,
        skills=sorted(skill.name for skill in candidate.skills),
    )


@app.post("/api/vacancies", response_model=schemas.VacancyCreatedResponse, status_code=201)
def create_vacancy(payload: schemas.VacancyCreate, db: Session = Depends(get_db)):
    normalized_level = normalize_level(payload.level)
    normalized_skill_names = sorted({name.strip() for name in payload.required_skills if name.strip()})
    if not normalized_skill_names:
        raise HTTPException(status_code=400, detail="At least one required skill is needed")

    existing_skills = (
        db.query(models.Skill)
        .filter(models.Skill.name.in_(normalized_skill_names))
        .all()
    )
    skill_map = {skill.name: skill for skill in existing_skills}

    for skill_name in normalized_skill_names:
        if skill_name not in skill_map:
            new_skill = models.Skill(name=skill_name)
            db.add(new_skill)
            db.flush()
            skill_map[skill_name] = new_skill

    vacancy = models.Vacancy(
        title=payload.title.strip(),
        company=payload.company.strip(),
        level=normalized_level,
        specialization=payload.specialization.strip().lower(),
        description=payload.description.strip(),
        required_skills=[skill_map[name] for name in normalized_skill_names],
    )
    db.add(vacancy)
    db.commit()
    db.refresh(vacancy)

    return schemas.VacancyCreatedResponse(
        id=vacancy.id,
        title=vacancy.title,
        company=vacancy.company,
        level=vacancy.level,
        specialization=vacancy.specialization,
        description=vacancy.description,
        required_skills=sorted(skill.name for skill in vacancy.required_skills),
    )


@app.get("/api/candidates/{candidate_id}/matches", response_model=schemas.CandidateMatchesResponse)
def get_candidate_matches(
    candidate_id: int,
    min_match_percent: float = Query(default=0.0, ge=0.0, le=100.0),
    level_filter: str | None = Query(default=None),
    specialization_filter: str | None = Query(default=None),
    db: Session = Depends(get_db),
):
    candidate = (
        db.query(models.Candidate)
        .options(joinedload(models.Candidate.skills))
        .filter(models.Candidate.id == candidate_id)
        .first()
    )
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")

    vacancies = db.query(models.Vacancy).options(joinedload(models.Vacancy.required_skills)).all()

    matches = []
    for vacancy in vacancies:
        if level_filter and vacancy.level != level_filter.strip().lower():
            continue
        if specialization_filter and specialization_filter.strip().lower() not in vacancy.specialization:
            continue
        percent, required_skills, matched_skills = calculate_match_percent(candidate, vacancy)
        if percent < min_match_percent:
            continue
        matches.append(
            schemas.VacancyMatch(
                vacancy_id=vacancy.id,
                title=vacancy.title,
                company=vacancy.company,
                level=vacancy.level,
                specialization=vacancy.specialization,
                match_percent=percent,
                required_skills=required_skills,
                matched_skills=matched_skills,
            )
        )

    matches.sort(key=lambda item: item.match_percent, reverse=True)
    return schemas.CandidateMatchesResponse(candidate=candidate, matches=matches)


@app.get("/", include_in_schema=False)
def serve_frontend():
    return FileResponse(BASE_DIR / "index.html")

