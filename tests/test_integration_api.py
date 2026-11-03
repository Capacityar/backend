from pathlib import Path
import pytest
from fastapi import status
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.modules.users.models import User


# ==============================================================================
# Helper Factories
# ==============================================================================

def create_user_helper(
    client: TestClient,
    email: str = "estudiante@example.com",
    first_name: str = "Test",
    last_name: str = "User",
    role: str = "student",
) -> dict:
    response = client.post(
        "/api/users",
        json={
            "first_name": first_name,
            "last_name": last_name,
            "email": email,
            "role": role,
        },
    )
    assert response.status_code == status.HTTP_201_CREATED
    return response.json()


def create_skill_helper(client: TestClient, name: str = "Python") -> dict:
    response = client.post("/api/skills", json={"name": name})
    assert response.status_code in (status.HTTP_201_CREATED, status.HTTP_200_OK)
    return response.json()


def create_job_description_helper(
    client: TestClient,
    company_user_id: int,
    skill_id: int,
    title: str = "Junior Backend Developer",
    province: str = "Buenos Aires",
) -> dict:
    response = client.post(
        "/api/job-descriptions",
        json={
            "user_id": company_user_id,
            "title": title,
            "description": "Búsqueda activa de desarrollador con conocimientos básicos.",
            "province": province,
            "required_skills": [
                {"skill_id": skill_id, "level": "INTERMEDIATE"}
            ],
        },
    )
    assert response.status_code == status.HTTP_201_CREATED
    return response.json()


# ==============================================================================
# Users API Tests (/api/users)
# ==============================================================================

def test_create_user_success(client: TestClient) -> None:
    payload = {
        "first_name": "Ana",
        "last_name": "Gomez",
        "email": "ana.gomez@example.com",
        "role": "student",
    }
    response = client.post("/api/users", json=payload)
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["id"] > 0
    assert data["email"] == "ana.gomez@example.com"
    assert data["first_name"] == "Ana"
    assert data["last_name"] == "Gomez"
    assert data["role"] == "student"
    assert "created_at" in data
    assert "updated_at" in data


def test_create_user_duplicate_email_conflict(client: TestClient) -> None:
    payload = {
        "first_name": "Ana",
        "last_name": "Gomez",
        "email": "duplicate@example.com",
        "role": "student",
    }
    first_res = client.post("/api/users", json=payload)
    assert first_res.status_code == status.HTTP_201_CREATED

    duplicate_res = client.post("/api/users", json=payload)
    assert duplicate_res.status_code == status.HTTP_409_CONFLICT
    assert duplicate_res.json()["detail"] == "Email already exists"


def test_get_user_by_id_success(client: TestClient) -> None:
    created = create_user_helper(client, email="get_user@example.com")
    user_id = created["id"]

    response = client.get(f"/api/users/{user_id}")
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["id"] == user_id
    assert response.json()["email"] == "get_user@example.com"


def test_get_user_nonexistent_not_found(client: TestClient) -> None:
    response = client.get("/api/users/99999")
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json()["detail"] == "User not found"


def test_list_users(client: TestClient) -> None:
    create_user_helper(client, email="u1@example.com")
    create_user_helper(client, email="u2@example.com")

    response = client.get("/api/users")
    assert response.status_code == status.HTTP_200_OK
    emails = [u["email"] for u in response.json()]
    assert len(emails) == 2
    assert "u1@example.com" in emails
    assert "u2@example.com" in emails


def test_delete_user_success_and_subsequent_not_found(client: TestClient) -> None:
    created = create_user_helper(client, email="delete_me@example.com")
    user_id = created["id"]

    del_response = client.delete(f"/api/users/{user_id}")
    assert del_response.status_code == status.HTTP_204_NO_CONTENT

    get_response = client.get(f"/api/users/{user_id}")
    assert get_response.status_code == status.HTTP_404_NOT_FOUND


def test_delete_user_nonexistent_not_found(client: TestClient) -> None:
    response = client.delete("/api/users/99999")
    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_update_user_success(client: TestClient) -> None:
    created = create_user_helper(client, email="update_target@example.com")
    user_id = created["id"]

    update_payload = {"first_name": "UpdatedName", "last_name": "UpdatedLast"}
    response = client.patch(f"/api/users/{user_id}", json=update_payload)
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["first_name"] == "UpdatedName"
    assert data["last_name"] == "UpdatedLast"
    assert data["email"] == "update_target@example.com"


def test_update_user_nonexistent_not_found(client: TestClient) -> None:
    response = client.patch("/api/users/99999", json={"first_name": "Ghost"})
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json()["detail"] == "User not found"


def test_update_user_duplicate_email_conflict(client: TestClient) -> None:
    create_user_helper(client, email="user_one@example.com")
    user2 = create_user_helper(client, email="user_two@example.com")

    # Attempt to change user2's email to user1's email
    response = client.patch(
        f"/api/users/{user2['id']}",
        json={"email": "user_one@example.com"},
    )
    assert response.status_code == status.HTTP_409_CONFLICT
    assert response.json()["detail"] == "Email already exists"


def test_list_users_filter_by_role(client: TestClient) -> None:
    create_user_helper(client, email="student_filter@example.com", role="student")
    create_user_helper(client, email="tutor_filter@example.com", role="tutor")

    response_students = client.get("/api/users?role=student")
    assert response_students.status_code == status.HTTP_200_OK
    student_emails = [u["email"] for u in response_students.json()]
    assert "student_filter@example.com" in student_emails
    assert "tutor_filter@example.com" not in student_emails


# ==============================================================================
# Skills & User Skills API Tests (/api/skills, /api/students/{email}/skills)
# ==============================================================================

def test_create_and_search_skills(client: TestClient) -> None:
    res_create = client.post("/api/skills", json={"name": "FastAPI"})
    assert res_create.status_code == status.HTTP_201_CREATED
    skill = res_create.json()
    assert skill["name"] == "FastAPI"

    res_search = client.get("/api/skills?q=Fast")
    assert res_search.status_code == status.HTTP_200_OK
    names = [s["name"] for s in res_search.json()]
    assert "FastAPI" in names


def test_add_skill_to_student_success(client: TestClient) -> None:
    student = create_user_helper(client, email="student_skill@example.com")
    skill = create_skill_helper(client, name="PostgreSQL")

    response = client.post(
        f"/api/students/{student['email']}/skills",
        json={"skill_id": skill["id"], "level": "BEGINNER"},
    )
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["skill_id"] == skill["id"]
    assert data["skill_name"] == "PostgreSQL"
    assert data["level"] == "BEGINNER"


def test_add_skill_to_student_duplicate_conflict(client: TestClient) -> None:
    student = create_user_helper(client, email="student_dup_skill@example.com")
    skill = create_skill_helper(client, name="TypeScript")

    payload = {"skill_id": skill["id"], "level": "INTERMEDIATE"}
    first = client.post(f"/api/students/{student['email']}/skills", json=payload)
    assert first.status_code == status.HTTP_201_CREATED

    duplicate = client.post(f"/api/students/{student['email']}/skills", json=payload)
    assert duplicate.status_code == status.HTTP_409_CONFLICT
    assert duplicate.json()["detail"] == "Skill already added"


def test_add_skill_nonexistent_student_not_found(client: TestClient) -> None:
    skill = create_skill_helper(client, name="Go")
    response = client.post(
        "/api/students/ghost@example.com/skills",
        json={"skill_id": skill["id"], "level": "ADVANCED"},
    )
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json()["detail"] == "User not found"


def test_add_skill_nonexistent_skill_not_found(client: TestClient) -> None:
    student = create_user_helper(client, email="valid_student@example.com")
    response = client.post(
        f"/api/students/{student['email']}/skills",
        json={"skill_id": 99999, "level": "PRO"},
    )
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json()["detail"] == "Skill not found"


def test_list_student_skills(client: TestClient) -> None:
    student = create_user_helper(client, email="list_skills@example.com")
    skill1 = create_skill_helper(client, name="React")
    skill2 = create_skill_helper(client, name="Next.js")

    client.post(
        f"/api/students/{student['email']}/skills",
        json={"skill_id": skill1["id"], "level": "ADVANCED"},
    )
    client.post(
        f"/api/students/{student['email']}/skills",
        json={"skill_id": skill2["id"], "level": "BEGINNER"},
    )

    response = client.get(f"/api/students/{student['email']}/skills")
    assert response.status_code == status.HTTP_200_OK
    skills = response.json()
    assert len(skills) == 2
    skill_names = [s["skill_name"] for s in skills]
    assert "React" in skill_names
    assert "Next.js" in skill_names


def test_delete_student_skill(client: TestClient) -> None:
    student = create_user_helper(client, email="delete_skill@example.com")
    skill = create_skill_helper(client, name="Docker")

    client.post(
        f"/api/students/{student['email']}/skills",
        json={"skill_id": skill["id"], "level": "INTERMEDIATE"},
    )

    del_res = client.delete(f"/api/students/{student['email']}/skills/{skill['id']}")
    assert del_res.status_code == status.HTTP_204_NO_CONTENT

    list_res = client.get(f"/api/students/{student['email']}/skills")
    assert list_res.status_code == status.HTTP_200_OK
    assert len(list_res.json()) == 0


def test_delete_student_skill_not_found(client: TestClient) -> None:
    student = create_user_helper(client, email="delete_absent_skill@example.com")
    skill = create_skill_helper(client, name="Kubernetes")

    del_res = client.delete(f"/api/students/{student['email']}/skills/{skill['id']}")
    assert del_res.status_code == status.HTTP_404_NOT_FOUND
    assert del_res.json()["detail"] == "Skill not in user's list"


def test_create_skill_idempotent_get_or_create(client: TestClient) -> None:
    # First post creates the skill -> 201 Created
    first_res = client.post("/api/skills", json={"name": "GraphQL"})
    assert first_res.status_code == status.HTTP_201_CREATED
    first_data = first_res.json()
    assert first_data["name"] == "GraphQL"

    # Second post with same name (case-insensitive) -> 200 OK
    second_res = client.post("/api/skills", json={"name": "graphql"})
    assert second_res.status_code == status.HTTP_200_OK
    second_data = second_res.json()
    assert second_data["id"] == first_data["id"]


def test_search_skills_empty_query_returns_empty_list(client: TestClient) -> None:
    create_skill_helper(client, name="Rust")
    # Empty query or whitespace should return empty list per service specification
    res_empty = client.get("/api/skills?q=")
    assert res_empty.status_code == status.HTTP_200_OK
    assert res_empty.json() == []


def test_list_student_skills_nonexistent_student_not_found(client: TestClient) -> None:
    response = client.get("/api/students/ghost_student@example.com/skills")
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json()["detail"] == "User not found"


def test_delete_student_skill_nonexistent_student_not_found(client: TestClient) -> None:
    response = client.delete("/api/students/ghost_student@example.com/skills/1")
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json()["detail"] == "User not found"


# ==============================================================================
# Job Descriptions API Tests (/api/job-descriptions)
# ==============================================================================

def test_create_job_description_success(client: TestClient) -> None:
    company = create_user_helper(
        client, email="hr@company.com", role="company_admin"
    )
    skill = create_skill_helper(client, name="Django")

    payload = {
        "user_id": company["id"],
        "title": "Backend Django Dev",
        "description": "Se busca desarrollador Django con experiencia.",
        "province": "Córdoba",
        "required_skills": [
            {"skill_id": skill["id"], "level": "INTERMEDIATE"}
        ],
    }
    response = client.post("/api/job-descriptions", json=payload)
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["id"] > 0
    assert data["title"] == "Backend Django Dev"
    assert data["province"] == "Córdoba"
    assert data["posted_by"]["email"] == "hr@company.com"
    assert len(data["required_skills"]) == 1
    assert data["required_skills"][0]["skill_name"] == "Django"


def test_create_job_description_forbidden_for_student(client: TestClient) -> None:
    student = create_user_helper(
        client, email="fake_recruiter@example.com", role="student"
    )
    skill = create_skill_helper(client, name="Vue")

    payload = {
        "user_id": student["id"],
        "title": "Unauthorized Posting",
        "description": "Should fail with 403 Forbidden.",
        "province": "Buenos Aires",
        "required_skills": [
            {"skill_id": skill["id"], "level": "BEGINNER"}
        ],
    }
    response = client.post("/api/job-descriptions", json=payload)
    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert "Only company_admin users can post job descriptions" in response.json()["detail"]


def test_create_job_description_nonexistent_user_not_found(client: TestClient) -> None:
    skill = create_skill_helper(client, name="Node.js")
    payload = {
        "user_id": 99999,
        "title": "Ghost Posting",
        "description": "Nonexistent user posting.",
        "province": "Mendoza",
        "required_skills": [
            {"skill_id": skill["id"], "level": "BEGINNER"}
        ],
    }
    response = client.post("/api/job-descriptions", json=payload)
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json()["detail"] == "User not found"


def test_list_job_descriptions(client: TestClient) -> None:
    company = create_user_helper(
        client, email="recruiter@enterprise.com", role="company_admin"
    )
    skill = create_skill_helper(client, name="C#")

    create_job_description_helper(
        client,
        company_user_id=company["id"],
        skill_id=skill["id"],
        title=".NET Developer",
        province="Santa Fe",
    )

    response = client.get("/api/job-descriptions")
    assert response.status_code == status.HTTP_200_OK
    assert len(response.json()) == 1
    assert any(jd["title"] == ".NET Developer" for jd in response.json())


def test_delete_job_description_success(client: TestClient) -> None:
    company = create_user_helper(
        client, email="delete_jd_hr@enterprise.com", role="company_admin"
    )
    skill = create_skill_helper(client, name="Ruby")
    jd = create_job_description_helper(
        client, company_user_id=company["id"], skill_id=skill["id"]
    )

    del_res = client.delete(f"/api/job-descriptions/{jd['id']}")
    assert del_res.status_code == status.HTTP_204_NO_CONTENT

    del_nonexistent = client.delete(f"/api/job-descriptions/{jd['id']}")
    assert del_nonexistent.status_code == status.HTTP_404_NOT_FOUND


def test_list_job_descriptions_filtered_by_province(client: TestClient) -> None:
    company = create_user_helper(
        client, email="geo_recruiter@enterprise.com", role="company_admin"
    )
    skill = create_skill_helper(client, name="Scala")

    create_job_description_helper(
        client,
        company_user_id=company["id"],
        skill_id=skill["id"],
        title="Scala Dev Cordoba",
        province="Córdoba",
    )
    create_job_description_helper(
        client,
        company_user_id=company["id"],
        skill_id=skill["id"],
        title="Scala Dev Mendoza",
        province="Mendoza",
    )

    res_cordoba = client.get("/api/job-descriptions?province=Córdoba")
    assert res_cordoba.status_code == status.HTTP_200_OK
    assert len(res_cordoba.json()) == 1
    assert res_cordoba.json()[0]["title"] == "Scala Dev Cordoba"

    res_empty = client.get("/api/job-descriptions?province=Tierra del Fuego")
    assert res_empty.status_code == status.HTTP_200_OK
    assert res_empty.json() == []


# ==============================================================================
# Learning Paths API Tests (/api/learning-paths)
# ==============================================================================

def _sample_gap_report(
    student_email: str = "carlos@example.com",
    all_ready: bool = False,
) -> dict:
    if all_ready:
        return {
            "student": {
                "name": "Carlos Gomez",
                "email": student_email,
                "skills": [{"name": "Python", "level": 3}],
                "interests": ["web development"],
            },
            "company": {"name": "Tech Corp"},
            "target_role": {
                "title": "Python Junior",
                "required_skills": [{"name": "Python", "level": 3, "priority": "HIGH"}],
            },
            "summary": "Estudiante listo para el puesto.",
            "readiness_score": 100,
            "skills": [
                {
                    "name": "Python",
                    "current_level": 3,
                    "required_level": 3,
                    "gap_level": 0,
                    "priority": "LOW",
                    "status": "READY",
                }
            ],
        }

    return {
        "student": {
            "name": "Carlos Gomez",
            "email": student_email,
            "skills": [{"name": "Python", "level": 1}],
            "interests": ["web development", "videojuegos"],
        },
        "company": {"name": "Tech Corp"},
        "target_role": {
            "title": "Junior Python Developer",
            "required_skills": [
                {"name": "Python", "level": 2, "priority": "HIGH"},
                {"name": "FastAPI", "level": 2, "priority": "MEDIUM"},
            ],
        },
        "summary": "Carlos requiere nivelar Python y FastAPI.",
        "readiness_score": 50,
        "skills": [
            {
                "name": "Python",
                "current_level": 1,
                "required_level": 2,
                "gap_level": 1,
                "priority": "HIGH",
                "status": "NEEDS_WORK",
            },
            {
                "name": "FastAPI",
                "current_level": 0,
                "required_level": 2,
                "gap_level": 2,
                "priority": "MEDIUM",
                "status": "MISSING",
            },
        ],
    }


def test_create_learning_path_with_mock_generator(client: TestClient) -> None:
    payload = _sample_gap_report(student_email="student_lp@example.com")
    response = client.post("/api/learning-paths", json=payload)
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["generator_used"] == "mock"
    assert data["student_email"] == "student_lp@example.com"
    assert data["status"] == "ACTIVE"
    assert data["id"] > 0
    assert len(data["modules"]) == 2


def test_create_learning_path_conflict_when_all_skills_ready(client: TestClient) -> None:
    payload = _sample_gap_report(student_email="expert@example.com", all_ready=True)
    response = client.post("/api/learning-paths", json=payload)
    assert response.status_code == status.HTTP_409_CONFLICT
    assert "El estudiante ya cumple todos los requerimientos" in response.json()["detail"]


def test_get_learning_path_by_id_and_not_found(client: TestClient) -> None:
    payload = _sample_gap_report(student_email="carlos_get@example.com")
    created = client.post("/api/learning-paths", json=payload).json()
    path_id = created["id"]

    res_get = client.get(f"/api/learning-paths/{path_id}")
    assert res_get.status_code == status.HTTP_200_OK
    assert res_get.json()["id"] == path_id
    assert res_get.json()["generator_used"] == "mock"

    res_404 = client.get("/api/learning-paths/99999")
    assert res_404.status_code == status.HTTP_404_NOT_FOUND
    assert "Learning path no encontrado" in res_404.json()["detail"]


def test_list_learning_paths_and_by_student(client: TestClient) -> None:
    payload = _sample_gap_report(student_email="student_filter@example.com")
    client.post("/api/learning-paths", json=payload)

    res_all = client.get("/api/learning-paths")
    assert res_all.status_code == status.HTTP_200_OK
    assert len(res_all.json()) == 1

    res_student = client.get("/api/students/student_filter@example.com/learning-paths")
    assert res_student.status_code == status.HTTP_200_OK
    assert len(res_student.json()) == 1
    assert res_student.json()[0]["student_email"] == "student_filter@example.com"


# ==============================================================================
# Attempts API Tests (/api/attempts)
# ==============================================================================

def test_attempt_nonexistent_learning_path_not_found(client: TestClient) -> None:
    payload = {
        "student_email": "student@example.com",
        "learning_path_id": 99999,
        "module_index": 0,
        "unit_index": 2,
        "exercise_index": 0,
        "answer": "respuesta de ejemplo",
        "time_spent_seconds": 30,
    }
    response = client.post("/api/attempts", json=payload)
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert "Learning path no encontrado" in response.json()["detail"]


def test_attempt_forbidden_for_different_student(client: TestClient) -> None:
    lp_payload = _sample_gap_report(student_email="owner@example.com")
    created_lp = client.post("/api/learning-paths", json=lp_payload).json()

    attempt_payload = {
        "student_email": "imposter@example.com",
        "learning_path_id": created_lp["id"],
        "module_index": 0,
        "unit_index": 2,
        "exercise_index": 0,
        "answer": "respuesta de ejemplo",
        "time_spent_seconds": 30,
    }
    response = client.post("/api/attempts", json=attempt_payload)
    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert "El learning path no pertenece a este estudiante" in response.json()["detail"]


def test_valid_attempt_evaluation_and_retrieval(client: TestClient) -> None:
    student_email = "student_attempts@example.com"
    lp_payload = _sample_gap_report(student_email=student_email)
    created_lp = client.post("/api/learning-paths", json=lp_payload).json()
    path_id = created_lp["id"]

    # In MockPlanGenerator: Module 0, Unit 2 (práctica) has:
    # Exercise 0: text, expected_answer = "respuesta de ejemplo"
    # Exercise 1: multiple_choice, expected_answer = "opcion correcta"

    # Happy path: correct answer
    correct_payload = {
        "student_email": student_email,
        "learning_path_id": path_id,
        "module_index": 0,
        "unit_index": 2,
        "exercise_index": 0,
        "answer": "respuesta de ejemplo",
        "time_spent_seconds": 45,
    }
    res_correct = client.post("/api/attempts", json=correct_payload)
    assert res_correct.status_code == status.HTTP_201_CREATED
    data_correct = res_correct.json()
    assert data_correct["id"] > 0
    assert data_correct["is_correct"] is True
    assert data_correct["score"] == 1.0
    assert data_correct["skill_mastery"] == 1.0
    assert data_correct["mastery_threshold_reached"] is True

    # Valid attempt: incorrect answer
    incorrect_payload = {
        "student_email": student_email,
        "learning_path_id": path_id,
        "module_index": 0,
        "unit_index": 2,
        "exercise_index": 0,
        "answer": "respuesta errónea",
        "time_spent_seconds": 25,
    }
    res_incorrect = client.post("/api/attempts", json=incorrect_payload)
    assert res_incorrect.status_code == status.HTTP_201_CREATED
    data_incorrect = res_incorrect.json()
    assert data_incorrect["is_correct"] is False
    assert data_incorrect["score"] == 0.0

    # Retrieve attempt by ID (200 OK)
    attempt_id = data_correct["id"]
    get_res = client.get(f"/api/attempts/{attempt_id}")
    assert get_res.status_code == status.HTTP_200_OK
    assert get_res.json()["id"] == attempt_id

    # Retrieve nonexistent attempt ID (404 Not Found)
    assert client.get("/api/attempts/99999").status_code == status.HTTP_404_NOT_FOUND

    # List attempts for student (200 OK)
    list_res = client.get(f"/api/students/{student_email}/attempts")
    assert list_res.status_code == status.HTTP_200_OK
    assert len(list_res.json()) == 2


def test_attempt_nonexistent_exercise_index_not_found(client: TestClient) -> None:
    student_email = "student_bad_idx@example.com"
    lp_payload = _sample_gap_report(student_email=student_email)
    created_lp = client.post("/api/learning-paths", json=lp_payload).json()

    # Unit 0 (pasión) has no exercises in MockPlanGenerator
    payload = {
        "student_email": student_email,
        "learning_path_id": created_lp["id"],
        "module_index": 0,
        "unit_index": 0,
        "exercise_index": 0,
        "answer": "test",
        "time_spent_seconds": 10,
    }
    response = client.post("/api/attempts", json=payload)
    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_attempt_nonexistent_module_index_not_found(client: TestClient) -> None:
    student_email = "student_bad_mod@example.com"
    lp_payload = _sample_gap_report(student_email=student_email)
    created_lp = client.post("/api/learning-paths", json=lp_payload).json()

    payload = {
        "student_email": student_email,
        "learning_path_id": created_lp["id"],
        "module_index": 99,
        "unit_index": 0,
        "exercise_index": 0,
        "answer": "test",
        "time_spent_seconds": 10,
    }
    response = client.post("/api/attempts", json=payload)
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert "El plan no tiene module_index=99" in response.json()["detail"]


# ==============================================================================
# Gap Analysis API Tests (/api/gap-analyses)
# ==============================================================================

def test_gap_analysis_creation_and_retrieval(client: TestClient) -> None:
    # 1. Setup Student
    student = create_user_helper(client, email="gap_student@example.com", role="student")
    # 2. Setup Company Admin
    company = create_user_helper(client, email="gap_hr@company.com", role="company_admin")
    # 3. Setup Skill and User Skill
    skill = create_skill_helper(client, name="SQL")
    client.post(
        f"/api/students/{student['email']}/skills",
        json={"skill_id": skill["id"], "level": "BEGINNER"},
    )
    # 4. Setup Job Description with required skill at ADVANCED level
    jd = create_job_description_helper(
        client,
        company_user_id=company["id"],
        skill_id=skill["id"],
        title="Data Engineer",
    )

    # 5. POST /api/gap-analyses -> 201 Created
    gap_payload = {
        "student_email": student["email"],
        "job_description_id": jd["id"],
    }
    create_res = client.post("/api/gap-analyses", json=gap_payload)
    assert create_res.status_code == status.HTTP_201_CREATED
    data = create_res.json()
    assert data["id"] > 0
    assert data["student_email"] == student["email"]
    assert data["generator_used"] == "skills"
    assert data["gap_report"] is not None
    assert len(data["gap_report"]["skills"]) == 1

    gap_id = data["id"]

    # 6. GET /api/gap-analyses/{gap_id} -> 200 OK
    get_res = client.get(f"/api/gap-analyses/{gap_id}")
    assert get_res.status_code == status.HTTP_200_OK
    assert get_res.json()["id"] == gap_id
    assert get_res.json()["student_email"] == student["email"]

    # 7. GET /api/gap-analyses/99999 -> 404 Not Found
    get_nonexistent = client.get("/api/gap-analyses/99999")
    assert get_nonexistent.status_code == status.HTTP_404_NOT_FOUND

    # 8. GET /api/students/{email}/gap-analyses -> 200 OK
    list_res = client.get(f"/api/students/{student['email']}/gap-analyses")
    assert list_res.status_code == status.HTTP_200_OK
    assert len(list_res.json()) == 1

    # 9. Step 2: POST /api/students/{email}/generate-learning-path -> 201 Created
    gen_lp_res = client.post(f"/api/students/{student['email']}/generate-learning-path")
    assert gen_lp_res.status_code == status.HTTP_201_CREATED
    gen_data = gen_lp_res.json()
    assert gen_data["gap_analysis"]["id"] == gap_id
    assert gen_data["gap_analysis"]["learning_path_id"] is not None
    assert gen_data["learning_path"]["generator_used"] == "mock"


def test_gap_analysis_nonexistent_student_or_jd_not_found(client: TestClient) -> None:
    # Nonexistent student -> 404
    res_no_student = client.post(
        "/api/gap-analyses",
        json={"student_email": "nonexistent@example.com", "job_description_id": 1},
    )
    assert res_no_student.status_code == status.HTTP_404_NOT_FOUND
    assert "Estudiante no encontrado" in res_no_student.json()["detail"]

    # Valid student, nonexistent JD -> 404
    student = create_user_helper(client, email="real_student@example.com")
    res_no_jd = client.post(
        "/api/gap-analyses",
        json={"student_email": student["email"], "job_description_id": 99999},
    )
    assert res_no_jd.status_code == status.HTTP_404_NOT_FOUND
    assert "Puesto no encontrado" in res_no_jd.json()["detail"]


def test_generate_learning_path_without_pending_gap_analysis_not_found(client: TestClient) -> None:
    # 1. Attempt generate-learning-path for student who has no gap analyses -> 404
    student = create_user_helper(client, email="no_gap_student@example.com")
    res_no_gap = client.post(f"/api/students/{student['email']}/generate-learning-path")
    assert res_no_gap.status_code == status.HTTP_404_NOT_FOUND
    assert "No hay gap_analysis pendiente" in res_no_gap.json()["detail"]

    # 2. Setup JD and student skill, create gap analysis
    company = create_user_helper(client, email="company_gap2@example.com", role="company_admin")
    skill = create_skill_helper(client, name="Rust")
    client.post(
        f"/api/students/{student['email']}/skills",
        json={"skill_id": skill["id"], "level": "BEGINNER"},
    )
    jd = create_job_description_helper(
        client, company_user_id=company["id"], skill_id=skill["id"], title="Rust Dev"
    )
    client.post(
        "/api/gap-analyses",
        json={"student_email": student["email"], "job_description_id": jd["id"]},
    )

    # 3. First generate-learning-path -> 201 Created
    first_gen = client.post(f"/api/students/{student['email']}/generate-learning-path")
    assert first_gen.status_code == status.HTTP_201_CREATED

    # 4. Immediate second generate-learning-path -> 404 Not Found (no longer pending)
    second_gen = client.post(f"/api/students/{student['email']}/generate-learning-path")
    assert second_gen.status_code == status.HTTP_404_NOT_FOUND
    assert "No hay gap_analysis pendiente" in second_gen.json()["detail"]


# ==============================================================================
# Robustness, Edge Cases & Fixture Interoperability Tests
# ==============================================================================

def test_health_check_endpoint(client: TestClient) -> None:
    response = client.get("/api/health")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["status"] == "ok"
    assert "environment" in data


def test_create_user_validation_error_unprocessable(client: TestClient) -> None:
    # Invalid email format should return 422 Unprocessable Entity
    response = client.post(
        "/api/users",
        json={
            "first_name": "Test",
            "last_name": "Invalid",
            "email": "not-an-email",
            "role": "student",
        },
    )
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


def test_list_users_pagination(client: TestClient) -> None:
    create_user_helper(client, email="page1@example.com")
    create_user_helper(client, email="page2@example.com")
    create_user_helper(client, email="page3@example.com")

    # Limit=1, offset=1 should return exactly 1 user
    response = client.get("/api/users?offset=1&limit=1")
    assert response.status_code == status.HTTP_200_OK
    assert len(response.json()) == 1
    assert response.json()[0]["email"] == "page2@example.com"


def test_search_skills_default_no_param_returns_empty_list(client: TestClient) -> None:
    create_skill_helper(client, name="Elixir")
    # Calling GET /api/skills without ?q= defaults to q="" and returns []
    response = client.get("/api/skills")
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == []


def test_create_job_description_empty_skills_unprocessable(client: TestClient) -> None:
    company = create_user_helper(client, email="empty_skills_hr@enterprise.com", role="company_admin")
    payload = {
        "user_id": company["id"],
        "title": "Invalid Posting",
        "description": "Missing skills",
        "province": "Buenos Aires",
        "required_skills": [],  # Min length 1 required
    }
    response = client.post("/api/job-descriptions", json=payload)
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


def test_attempt_nonexistent_unit_index_not_found(client: TestClient) -> None:
    student_email = "student_bad_unit@example.com"
    lp_payload = _sample_gap_report(student_email=student_email)
    created_lp = client.post("/api/learning-paths", json=lp_payload).json()

    payload = {
        "student_email": student_email,
        "learning_path_id": created_lp["id"],
        "module_index": 0,
        "unit_index": 99,
        "exercise_index": 0,
        "answer": "test",
        "time_spent_seconds": 10,
    }
    response = client.post("/api/attempts", json=payload)
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert "El modulo no tiene unit_index=99" in response.json()["detail"]


def test_attempt_multiple_choice_exercise_evaluation(client: TestClient) -> None:
    student_email = "student_mc@example.com"
    lp_payload = _sample_gap_report(student_email=student_email)
    created_lp = client.post("/api/learning-paths", json=lp_payload).json()
    path_id = created_lp["id"]

    # MockPlanGenerator: Module 0, Unit 2, Exercise 1 is multiple_choice with expected_answer = "opcion correcta"
    # Happy path: correct answer with uppercase variation (case-insensitive multiple choice)
    correct_payload = {
        "student_email": student_email,
        "learning_path_id": path_id,
        "module_index": 0,
        "unit_index": 2,
        "exercise_index": 1,
        "answer": "OPCION CORRECTA",
        "time_spent_seconds": 15,
    }
    res_correct = client.post("/api/attempts", json=correct_payload)
    assert res_correct.status_code == status.HTTP_201_CREATED
    data_correct = res_correct.json()
    assert data_correct["is_correct"] is True
    assert data_correct["score"] == 1.0

    # Incorrect choice
    incorrect_payload = {
        "student_email": student_email,
        "learning_path_id": path_id,
        "module_index": 0,
        "unit_index": 2,
        "exercise_index": 1,
        "answer": "OPCION INCORRECTA",
        "time_spent_seconds": 12,
    }
    res_incorrect = client.post("/api/attempts", json=incorrect_payload)
    assert res_incorrect.status_code == status.HTTP_201_CREATED
    data_incorrect = res_incorrect.json()
    assert data_incorrect["is_correct"] is False
    assert data_incorrect["score"] == 0.0


def test_attempt_student_email_case_insensitive_match(client: TestClient) -> None:
    # LP created with mixed-case student email
    student_email_mixed = "Student_Case@example.com"
    lp_payload = _sample_gap_report(student_email=student_email_mixed)
    created_lp = client.post("/api/learning-paths", json=lp_payload).json()
    path_id = created_lp["id"]

    # Attempt submitted with lowercase email should be accepted (not 403)
    attempt_payload = {
        "student_email": "student_case@example.com",
        "learning_path_id": path_id,
        "module_index": 0,
        "unit_index": 2,
        "exercise_index": 0,
        "answer": "respuesta de ejemplo",
        "time_spent_seconds": 20,
    }
    response = client.post("/api/attempts", json=attempt_payload)
    assert response.status_code == status.HTTP_201_CREATED
    assert response.json()["is_correct"] is True


def test_list_student_learning_paths_empty_returns_empty_list(client: TestClient) -> None:
    response = client.get("/api/students/ghost_lp@example.com/learning-paths")
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == []


def test_list_student_attempts_empty_returns_empty_list(client: TestClient) -> None:
    response = client.get("/api/students/ghost_att@example.com/attempts")
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == []


def test_list_student_gap_analyses_empty_returns_empty_list(client: TestClient) -> None:
    response = client.get("/api/students/ghost_gap@example.com/gap-analyses")
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == []


def test_db_session_and_client_shared_database(client: TestClient, db_session: Session) -> None:
    # 1. Create user through HTTP client
    user_data = create_user_helper(client, email="shared_db@example.com")
    user_id = user_data["id"]

    # 2. Directly query database through db_session fixture
    db_user = db_session.get(User, user_id)
    assert db_user is not None
    assert db_user.email == "shared_db@example.com"

    # 3. Direct ORM update committed through db_session
    db_user.first_name = "DirectlyModified"
    db_session.commit()

    # 4. Query via HTTP client sees the update immediately
    response = client.get(f"/api/users/{user_id}")
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["first_name"] == "DirectlyModified"


def test_db_error_and_transaction_rollback_recovery(client: TestClient, db_session: Session) -> None:
    # 1. Create user via HTTP client
    create_user_helper(client, email="pre_error@example.com")

    # 2. Provoke an IntegrityError directly on db_session without manual rollback
    dup_user = User(
        first_name="Dup",
        last_name="User",
        email="pre_error@example.com",
        role="student",
    )
    db_session.add(dup_user)
    with pytest.raises(Exception):
        db_session.flush()

    # 3. The client must continue to work seamlessly without PendingRollbackError
    response = client.get("/api/users")
    assert response.status_code == status.HTTP_200_OK
    emails = [u["email"] for u in response.json()]
    assert "pre_error@example.com" in emails


def test_job_description_posted_by_deleted_user(client: TestClient) -> None:
    company = create_user_helper(client, email="temp_company@enterprise.com", role="company_admin")
    skill = create_skill_helper(client, name="GoLang")
    jd = create_job_description_helper(
        client,
        company_user_id=company["id"],
        skill_id=skill["id"],
        title="Go Backend Developer",
    )
    # Delete the company admin user
    del_res = client.delete(f"/api/users/{company['id']}")
    assert del_res.status_code == status.HTTP_204_NO_CONTENT

    # List job descriptions - should show [Eliminado] fallback
    list_res = client.get("/api/job-descriptions")
    assert list_res.status_code == status.HTTP_200_OK
    matching = [item for item in list_res.json() if item["id"] == jd["id"]]
    assert len(matching) == 1
    assert matching[0]["posted_by"]["id"] == 0
    assert matching[0]["posted_by"]["first_name"] == "[Eliminado]"


def test_gap_analysis_for_student_with_zero_skills(client: TestClient) -> None:
    student = create_user_helper(client, email="zero_skills_student@example.com", role="student")
    company = create_user_helper(client, email="zero_skills_hr@company.com", role="company_admin")
    skill = create_skill_helper(client, name="Kotlin")
    jd = create_job_description_helper(
        client, company_user_id=company["id"], skill_id=skill["id"], title="Kotlin Dev"
    )

    gap_res = client.post(
        "/api/gap-analyses",
        json={"student_email": student["email"], "job_description_id": jd["id"]},
    )
    assert gap_res.status_code == status.HTTP_201_CREATED
    data = gap_res.json()
    assert data["readiness_score"] == 0
    assert len(data["gap_report"]["skills"]) == 1
    assert data["gap_report"]["skills"][0]["status"] == "MISSING"

    # And generating path succeeds
    gen_res = client.post(f"/api/students/{student['email']}/generate-learning-path")
    assert gen_res.status_code == status.HTTP_201_CREATED
    assert gen_res.json()["learning_path"]["generator_used"] == "mock"


def test_learning_paths_pagination(client: TestClient) -> None:
    client.post("/api/learning-paths", json=_sample_gap_report(student_email="page_s1@example.com"))
    client.post("/api/learning-paths", json=_sample_gap_report(student_email="page_s2@example.com"))

    response = client.get("/api/learning-paths?offset=1&limit=1")
    assert response.status_code == status.HTTP_200_OK
    assert len(response.json()) == 1


def test_attempts_pagination(client: TestClient) -> None:
    student_email = "student_att_page@example.com"
    lp = client.post("/api/learning-paths", json=_sample_gap_report(student_email=student_email)).json()
    for _ in range(3):
        client.post(
            "/api/attempts",
            json={
                "student_email": student_email,
                "learning_path_id": lp["id"],
                "module_index": 0,
                "unit_index": 2,
                "exercise_index": 0,
                "answer": "respuesta de ejemplo",
                "time_spent_seconds": 10,
            },
        )
    res_page = client.get(f"/api/students/{student_email}/attempts?offset=1&limit=1")
    assert res_page.status_code == status.HTTP_200_OK
    assert len(res_page.json()) == 1


def test_create_job_description_tutor_or_admin_forbidden(client: TestClient) -> None:
    tutor = create_user_helper(client, email="tutor_posting@example.com", role="tutor")
    admin = create_user_helper(client, email="admin_posting@example.com", role="admin")
    skill = create_skill_helper(client, name="Swift")

    for u in (tutor, admin):
        res = client.post(
            "/api/job-descriptions",
            json={
                "user_id": u["id"],
                "title": "Forbidden Posting",
                "description": "Cannot be posted by non-company_admin",
                "province": "Buenos Aires",
                "required_skills": [{"skill_id": skill["id"], "level": "BEGINNER"}],
            },
        )
        assert res.status_code == status.HTTP_403_FORBIDDEN


def test_update_user_invalid_role_unprocessable(client: TestClient) -> None:
    user = create_user_helper(client, email="role_test@example.com")
    res = client.patch(f"/api/users/{user['id']}", json={"role": "superadmin"})
    assert res.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


def test_attempt_whitespace_answer_evaluation(client: TestClient) -> None:
    student_email = "student_whitespace@example.com"
    lp = client.post("/api/learning-paths", json=_sample_gap_report(student_email=student_email)).json()
    res = client.post(
        "/api/attempts",
        json={
            "student_email": student_email,
            "learning_path_id": lp["id"],
            "module_index": 0,
            "unit_index": 2,
            "exercise_index": 0,
            "answer": "     ",
            "time_spent_seconds": 5,
        },
    )
    assert res.status_code == status.HTTP_201_CREATED
    data = res.json()
    assert data["is_correct"] is False
    assert data["score"] == 0.0


def test_zero_disk_database_leakage(client: TestClient) -> None:
    disk_db = Path("capacity_ar_local.db")
    assert disk_db.exists(), "capacity_ar_local.db must exist for leakage check"
    initial_stat = disk_db.stat()

    # Perform a full set of CRUD operations
    u = create_user_helper(client, email="leak_check@example.com")
    s = create_skill_helper(client, name="LeakProofDB")
    client.get("/api/users")
    client.delete(f"/api/users/{u['id']}")

    final_stat = disk_db.stat()
    assert initial_stat.st_mtime == final_stat.st_mtime
    assert initial_stat.st_size == final_stat.st_size

