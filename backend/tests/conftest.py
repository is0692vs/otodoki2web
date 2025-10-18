"""Shared test fixtures for pytest."""
from __future__ import annotations

import os
from typing import AsyncGenerator

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlmodel import SQLModel

from app.db import models  # noqa: F401 - ensure models are registered

# Use in-memory SQLite for tests
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture(scope="session", autouse=True)
def configure_test_env() -> None:
    """Configure environment variables for tests."""
    os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key")
    os.environ.setdefault("JWT_REFRESH_SECRET_KEY", "test-refresh-secret-key")
    os.environ.setdefault("JWT_ALGORITHM", "HS256")


@pytest_asyncio.fixture
async def async_session() -> AsyncGenerator[AsyncSession, None]:
    """Provide an async database session for tests."""
    test_engine = create_async_engine(TEST_DATABASE_URL, future=True)
    
    # Create all tables
    async with test_engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
    
    # Create session factory
    async_session_factory = async_sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    
    # Provide session
    async with async_session_factory() as session:
        yield session
    
    # Cleanup
    await test_engine.dispose()
