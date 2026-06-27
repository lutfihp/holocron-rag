from app.core.config import Settings


def test_settings_loads_from_env(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://u:p@h/db")
    monkeypatch.setenv("TEST_DATABASE_URL", "postgresql+asyncpg://u:p@h/db_test")
    monkeypatch.setenv("JWT_SECRET", "secret-x")
    monkeypatch.setenv("JWT_ALGORITHM", "HS256")
    monkeypatch.setenv("JWT_TTL_HOURS", "12")
    monkeypatch.setenv("COOKIE_NAME", "session")
    monkeypatch.setenv("COOKIE_SECURE", "false")
    monkeypatch.setenv("CORS_ORIGINS", "http://localhost:3000,http://localhost:3001")

    s = Settings()
    assert s.database_url == "postgresql+asyncpg://u:p@h/db"
    assert s.jwt_ttl_hours == 12
    assert s.cookie_secure is False
    assert s.cors_origins == ["http://localhost:3000", "http://localhost:3001"]
