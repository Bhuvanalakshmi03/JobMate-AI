"""Unit and API tests for career profiles, skills management, validation, and isolation."""

from __future__ import annotations

import httpx

from app.core.config import Settings
from app.main import create_app


async def _login_user(
    client: httpx.AsyncClient,
    *,
    email: str,
    full_name: str,
) -> str:
    res = await client.post(
        "/api/v1/auth/dev-login",
        json={"email": email, "full_name": full_name},
    )
    assert res.status_code == 200
    return str(res.json()["access_token"])


async def test_profile_and_skills_crud_and_validation(
    migrated_test_app: object,
    test_settings: Settings,
) -> None:
    _ = migrated_test_app  # Ensures Alembic migration ran on test_settings.database_url
    dev_settings = test_settings.model_copy(update={"dev_auth_enabled": True})
    app = create_app(settings=dev_settings)

    async with app.router.lifespan_context(app):
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            # Unauthorized profile access rejected
            unauth = await client.get("/api/v1/profile")
            assert unauth.status_code == 401

            token = await _login_user(
                client, email="priya@university.edu", full_name="Priya Sharma"
            )
            headers = {"Authorization": f"Bearer {token}"}

            # Missing profile initially returns 404
            missing = await client.get("/api/v1/profile", headers=headers)
            assert missing.status_code == 404

            # Invalid timezone / javascript URL rejected with 422
            bad_tz = await client.post(
                "/api/v1/profile",
                headers=headers,
                json={"timezone": "Mars/Olympus", "github_url": "javascript:alert(1)"},
            )
            assert bad_tz.status_code == 422

            # Create profile
            created = await client.post(
                "/api/v1/profile",
                headers=headers,
                json={
                    "timezone": "Asia/Kolkata",
                    "headline": "CS Undergrad seeking Backend Engineer Internships",
                    "university": "NIT Trichy",
                    "degree": "B.Tech Computer Science",
                    "graduation_year": 2027,
                    "experience_level": "student",
                    "target_roles": ["Backend Engineer", "backend engineer", "AI Engineer"],
                    "preferred_locations": ["Bengaluru", "Remote"],
                    "work_mode_preferences": ["hybrid", "remote"],
                    "github_url": "https://github.com/priyasharma",
                    "ai_consent_given": True,
                },
            )
            assert created.status_code == 201
            body = created.json()
            assert body["timezone"] == "Asia/Kolkata"
            assert body["target_roles"] == ["Backend Engineer", "AI Engineer"]
            assert body["ai_consent_given"] is True

            # Duplicate POST fails with 409
            dup = await client.post("/api/v1/profile", headers=headers, json={})
            assert dup.status_code == 409

            # PUT updates profile cleanly
            updated = await client.put(
                "/api/v1/profile",
                headers=headers,
                json={
                    "full_name": "Priya K. Sharma",
                    "headline": "Final Year CS Student",
                    "work_mode_preferences": ["remote"],
                    "ai_consent_given": True,
                },
            )
            assert updated.status_code == 200
            assert updated.json()["full_name"] == "Priya K. Sharma"
            assert updated.json()["headline"] == "Final Year CS Student"

            # PUT skills normalizes and deduplicates
            skills_res = await client.put(
                "/api/v1/profile/skills",
                headers=headers,
                json={
                    "skills": [
                        {"name": "Python", "category": "language", "proficiency": "advanced"},
                        {"name": " python ", "category": "language", "proficiency": "expert"},
                        {"name": "FastAPI", "category": "framework", "proficiency": "advanced"},
                    ]
                },
            )
            assert skills_res.status_code == 200
            skills_data = skills_res.json()
            assert skills_data["total"] == 2
            names = {s["normalized_name"]: s["proficiency"] for s in skills_data["skills"]}
            assert names == {"python": "expert", "fastapi": "advanced"}


async def test_cross_user_profile_and_skills_isolation(
    migrated_test_app: object,
    test_settings: Settings,
) -> None:
    _ = migrated_test_app
    dev_settings = test_settings.model_copy(update={"dev_auth_enabled": True})
    app = create_app(settings=dev_settings)

    async with app.router.lifespan_context(app):
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            token_a = await _login_user(client, email="usera@college.edu", full_name="User A")
            token_b = await _login_user(client, email="userb@college.edu", full_name="User B")
            headers_a = {"Authorization": f"Bearer {token_a}"}
            headers_b = {"Authorization": f"Bearer {token_b}"}

            await client.post(
                "/api/v1/profile",
                headers=headers_a,
                json={"headline": "User A Secret Headline", "location": "Boston"},
            )
            await client.put(
                "/api/v1/profile/skills",
                headers=headers_a,
                json={"skills": [{"name": "Rust", "category": "language"}]},
            )

            # User B must not see User A's profile or skills
            b_profile = await client.get("/api/v1/profile", headers=headers_b)
            assert b_profile.status_code == 404

            b_skills = await client.get("/api/v1/profile/skills", headers=headers_b)
            assert b_skills.status_code == 200
            assert b_skills.json()["total"] == 0

            # User B creates their own data; User A's data remains untouched
            await client.put(
                "/api/v1/profile",
                headers=headers_b,
                json={"headline": "User B Headline"},
            )
            await client.put(
                "/api/v1/profile/skills",
                headers=headers_b,
                json={"skills": [{"name": "TypeScript", "category": "language"}]},
            )

            a_profile_after = await client.get("/api/v1/profile", headers=headers_a)
            assert a_profile_after.status_code == 200
            assert a_profile_after.json()["headline"] == "User A Secret Headline"

            a_skills_after = await client.get("/api/v1/profile/skills", headers=headers_a)
            assert [s["name"] for s in a_skills_after.json()["skills"]] == ["Rust"]

