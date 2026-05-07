import pytest
from pathlib import Path


@pytest.fixture
def tmp_cache(tmp_path: Path) -> Path:
    return tmp_path / "citrix-mcp-cache"
