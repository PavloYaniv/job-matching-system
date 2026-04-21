from pydantic import BaseModel


class CandidateBase(BaseModel):
    id: int
    full_name: str
    level: str
    desired_position: str

    class Config:
        from_attributes = True


class VacancyMatch(BaseModel):
    vacancy_id: int
    title: str
    company: str
    level: str
    specialization: str
    match_percent: float
    required_skills: list[str]
    matched_skills: list[str]


class CandidateMatchesResponse(BaseModel):
    candidate: CandidateBase
    matches: list[VacancyMatch]


class SkillBase(BaseModel):
    id: int
    name: str

    class Config:
        from_attributes = True


class CandidateCreate(BaseModel):
    full_name: str
    level: str
    desired_position: str
    skills: list[str]


class CandidateCreatedResponse(BaseModel):
    id: int
    full_name: str
    level: str
    desired_position: str
    skills: list[str]


class VacancyCreate(BaseModel):
    title: str
    company: str
    level: str
    specialization: str
    description: str
    required_skills: list[str]


class VacancyCreatedResponse(BaseModel):
    id: int
    title: str
    company: str
    level: str
    specialization: str
    description: str
    required_skills: list[str]

