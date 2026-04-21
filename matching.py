from models import Candidate, Vacancy


def calculate_match_percent(candidate: Candidate, vacancy: Vacancy) -> tuple[float, list[str], list[str]]:
    candidate_skills = {skill.name.strip().lower() for skill in candidate.skills}
    vacancy_skills = {skill.name.strip().lower() for skill in vacancy.required_skills}

    if not vacancy_skills:
        return 0.0, [], []

    intersection = candidate_skills.intersection(vacancy_skills)
    match_percent = (len(intersection) / len(vacancy_skills)) * 100

    required_skills_sorted = sorted(vacancy_skills)
    matched_skills_sorted = sorted(intersection)
    return round(match_percent, 2), required_skills_sorted, matched_skills_sorted

