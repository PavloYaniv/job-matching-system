const API_BASE_URL = "/api";
const API_BASE = 'http://localhost:8000';
const candidateSelect = document.getElementById("candidateSelect");
const candidateSearchInput = document.getElementById("candidateSearch");
const clearSearchBtn = document.getElementById("clearSearchBtn");
const prevCandidatesBtn = document.getElementById("prevCandidatesBtn");
const nextCandidatesBtn = document.getElementById("nextCandidatesBtn");
const candidatePageInfo = document.getElementById("candidatePageInfo");
const minMatchPercentSelect = document.getElementById("minMatchPercent");
const levelFilterSelect = document.getElementById("levelFilter");
const specializationFilterSelect = document.getElementById("specializationFilter");
const loadBtn = document.getElementById("loadBtn");
const results = document.getElementById("results");
const candidateForm = document.getElementById("candidateForm");
const vacancyForm = document.getElementById("vacancyForm");
const candidateSkillsSelect = document.getElementById("candidateSkillsSelect");
const vacancySkillsSelect = document.getElementById("vacancySkillsSelect");
const candidateFormStatus = document.getElementById("candidateFormStatus");
const vacancyFormStatus = document.getElementById("vacancyFormStatus");
const CANDIDATES_PAGE_SIZE = 20;
let allCandidates = [];
let filteredCandidates = [];
let currentCandidatesPage = 1;

function getSelectedValues(selectElement) {
    return Array.from(selectElement.selectedOptions).map((option) => option.value);
}

function enableEasyMultiSelect(selectElement) {
    selectElement.addEventListener("mousedown", (event) => {
        const target = event.target;
        if (target.tagName !== "OPTION") {
            return;
        }
        event.preventDefault();
        target.selected = !target.selected;
    });
}

async function fetchCandidates() {
    const response = await fetch(`${API_BASE_URL}/candidates`);
    if (!response.ok) {
        throw new Error("Не вдалося завантажити список кандидатів");
    }
    return response.json();
}

function renderCandidates(candidates) {
    candidateSelect.innerHTML = "";
    if (!candidates.length) {
        const option = document.createElement("option");
        option.value = "";
        option.textContent = "Кандидатів не знайдено";
        candidateSelect.appendChild(option);
        candidateSelect.disabled = true;
        return;
    }

    candidateSelect.disabled = false;
    candidates.forEach((candidate) => {
        const option = document.createElement("option");
        option.value = candidate.id;
        option.textContent = candidate.full_name;
        candidateSelect.appendChild(option);
    });
}

function paginateCandidates() {
    const totalPages = Math.max(1, Math.ceil(filteredCandidates.length / CANDIDATES_PAGE_SIZE));
    if (currentCandidatesPage > totalPages) {
        currentCandidatesPage = totalPages;
    }
    const startIdx = (currentCandidatesPage - 1) * CANDIDATES_PAGE_SIZE;
    const pageCandidates = filteredCandidates.slice(startIdx, startIdx + CANDIDATES_PAGE_SIZE);
    renderCandidates(pageCandidates);

    candidatePageInfo.textContent = `Сторінка ${currentCandidatesPage} з ${totalPages}`;
    prevCandidatesBtn.disabled = currentCandidatesPage <= 1;
    nextCandidatesBtn.disabled = currentCandidatesPage >= totalPages;
}

function applyCandidateFilter() {
    const query = candidateSearchInput.value.trim().toLowerCase();
    filteredCandidates = allCandidates.filter((candidate) =>
        candidate.full_name.toLowerCase().includes(query)
    );
    currentCandidatesPage = 1;
    paginateCandidates();
}

function createVacancyCard(match) {
    const card = document.createElement("article");
    card.className = "vacancy";

    const title = document.createElement("h3");
    title.textContent = `${match.title} (${match.company})`;

    const percent = document.createElement("p");
    percent.className = "meta";
    percent.textContent = `Відсоток збігу: ${match.match_percent}%`;

    const vacancyMeta = document.createElement("p");
    vacancyMeta.className = "small";
    vacancyMeta.textContent = `Рівень: ${match.level} | Спеціалізація: ${match.specialization}`;

    const progress = document.createElement("div");
    progress.className = "progress";

    const fill = document.createElement("div");
    fill.className = "progress-fill";
    fill.style.width = `${match.match_percent}%`;
    progress.appendChild(fill);

    const req = document.createElement("p");
    req.className = "small";
    req.textContent = `Необхідні навички: ${match.required_skills.join(", ") || "—"}`;

    const has = document.createElement("p");
    has.className = "small";
    has.textContent = `Спільні навички: ${match.matched_skills.join(", ") || "—"}`;

    card.append(title, percent, vacancyMeta, progress, req, has);
    return card;
}

async function loadMatches() {
    const candidateId = candidateSelect.value;
    if (!candidateId) {
        return;
    }

    const minMatchPercent = Number(minMatchPercentSelect.value);
    const levelFilter = levelFilterSelect.value;
    const specializationFilter = specializationFilterSelect.value;

    const params = new URLSearchParams({
        min_match_percent: String(minMatchPercent),
    });
    if (levelFilter) {
        params.append("level_filter", levelFilter);
    }
    if (specializationFilter) {
        params.append("specialization_filter", specializationFilter);
    }

    const response = await fetch(`${API_BASE_URL}/candidates/${candidateId}/matches?${params.toString()}`);
    if (!response.ok) {
        throw new Error("Не вдалося завантажити результати метчингу");
    }
    const data = await response.json();

    results.innerHTML = "";
    data.matches.forEach((match) => results.appendChild(createVacancyCard(match)));
}

async function createCandidate(event) {
    event.preventDefault();
    const formData = new FormData(candidateForm);
    const payload = {
        full_name: String(formData.get("full_name") || "").trim(),
        level: String(formData.get("level") || "").trim(),
        desired_position: String(formData.get("desired_position") || "").trim(),
        skills: getSelectedValues(candidateSkillsSelect),
    };

    if (!payload.skills.length) {
        candidateFormStatus.textContent = "Вкажіть хоча б одну навичку кандидата.";
        return;
    }

    const response = await fetch(`${API_BASE_URL}/candidates`, {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
        },
        body: JSON.stringify(payload),
    });

    if (!response.ok) {
        throw new Error("Не вдалося додати кандидата");
    }

    const created = await response.json();
    candidateForm.reset();
    candidateFormStatus.textContent = `Кандидата додано: ${created.full_name} (ID ${created.id}).`;

    allCandidates = await fetchCandidates();
    applyCandidateFilter();
    candidateSearchInput.value = created.full_name;
    applyCandidateFilter();
    candidateSelect.value = String(created.id);
}

async function createVacancy(event) {
    event.preventDefault();
    const formData = new FormData(vacancyForm);
    const payload = {
        title: String(formData.get("title") || "").trim(),
        company: String(formData.get("company") || "").trim(),
        level: String(formData.get("level") || "").trim(),
        specialization: String(formData.get("specialization") || "").trim(),
        description: String(formData.get("description") || "").trim(),
        required_skills: getSelectedValues(vacancySkillsSelect),
    };

    if (!payload.required_skills.length) {
        vacancyFormStatus.textContent = "Вкажіть хоча б одну вимогу до вакансії.";
        return;
    }

    const response = await fetch(`${API_BASE_URL}/vacancies`, {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
        },
        body: JSON.stringify(payload),
    });

    if (!response.ok) {
        throw new Error("Не вдалося додати вакансію");
    }

    const created = await response.json();
    vacancyForm.reset();
    vacancyFormStatus.textContent = `Вакансію додано: ${created.title} (ID ${created.id}).`;
}

async function init() {
    try {
        allCandidates = await fetchCandidates();
        filteredCandidates = [...allCandidates];
        paginateCandidates();
        enableEasyMultiSelect(candidateSkillsSelect);
        enableEasyMultiSelect(vacancySkillsSelect);
        feather.replace();
    } catch (error) {
        results.textContent = error.message;
    }
}

loadBtn.addEventListener("click", async () => {
    try {
        await loadMatches();
    } catch (error) {
        results.textContent = error.message;
    }
});

candidateForm.addEventListener("submit", async (event) => {
    try {
        await createCandidate(event);
    } catch (error) {
        candidateFormStatus.textContent = error.message;
    }
});

vacancyForm.addEventListener("submit", async (event) => {
    try {
        await createVacancy(event);
    } catch (error) {
        vacancyFormStatus.textContent = error.message;
    }
});

candidateSearchInput.addEventListener("input", applyCandidateFilter);

clearSearchBtn.addEventListener("click", () => {
    candidateSearchInput.value = "";
    applyCandidateFilter();
});

prevCandidatesBtn.addEventListener("click", () => {
    currentCandidatesPage -= 1;
    paginateCandidates();
});

nextCandidatesBtn.addEventListener("click", () => {
    currentCandidatesPage += 1;
    paginateCandidates();
});

init();
