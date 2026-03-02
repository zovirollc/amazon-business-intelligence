"""Pytest fixtures for amazon-business-intelligence tests."""
import os
import pytest
from pathlib import Path

@pytest.fixture
def project_root():
    return Path(__file__).parent.parent

@pytest.fixture
def data_warehouse(tmp_path):
    from data.warehouse import DataWarehouse
    return DataWarehouse(str(tmp_path / "data"))
