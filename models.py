from sqlalchemy import Column, ForeignKey, Integer, String, Table, Text
from sqlalchemy.orm import relationship

from database import Base

candidate_skills = Table(
    "candidate_skills",
    Base.metadata,
    Column("candidate_id", Integer, ForeignKey("candidates.id"), primary_key=True),
    Column("skill_id", Integer, ForeignKey("skills.id"), primary_key=True),
)

vacancy_skills = Table(
    "vacancy_skills",
    Base.metadata,
    Column("vacancy_id", Integer, ForeignKey("vacancies.id"), primary_key=True),
    Column("skill_id", Integer, ForeignKey("skills.id"), primary_key=True),
)


class Candidate(Base):
    __tablename__ = "candidates"

    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String(255), nullable=False)
    university = Column(String(255), nullable=False)
    specialty = Column(String(255), nullable=False)
    level = Column(String(50), nullable=False, default="junior")
    desired_position = Column(String(255), nullable=False, default="Junior Developer")

    skills = relationship("Skill", secondary=candidate_skills, back_populates="candidates")


class Vacancy(Base):
    __tablename__ = "vacancies"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    company = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    level = Column(String(50), nullable=False, default="junior")
    specialization = Column(String(255), nullable=False, default="Software Development")

    required_skills = relationship("Skill", secondary=vacancy_skills, back_populates="vacancies")


class Skill(Base):
    __tablename__ = "skills"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False)

    candidates = relationship("Candidate", secondary=candidate_skills, back_populates="skills")
    vacancies = relationship("Vacancy", secondary=vacancy_skills, back_populates="required_skills")

