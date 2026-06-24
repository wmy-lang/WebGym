"""pytest 全局 fixture。"""
from __future__ import annotations

import pytest

from app import create_app


@pytest.fixture
def app():
    app = create_app("test")
    yield app


@pytest.fixture
def client(app):
    return app.test_client()
