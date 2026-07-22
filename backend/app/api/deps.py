"""의존성 조립 지점 (composition root).

**구현체를 직접 import 하는 곳은 여기 하나뿐이다.**
라우터와 서비스는 `app.ports.*` 의 Protocol 타입만 안다.
사내 이식은 이 파일에서 어댑터를 바꿔 끼우는 것으로 끝나야 한다.

테스트는 `app.dependency_overrides[get_spec_repository]` 로
가짜 구현을 밀어 넣는다.
"""

from functools import lru_cache
from typing import Annotated

from fastapi import Depends

from app.adapters.local.file_spec_repository import FileSpecRepository
from app.core.config import settings
from app.ports.spec_repository import SpecRepository


@lru_cache(maxsize=1)
def get_spec_repository() -> SpecRepository:
    """로컬 파일 저장소. 사내에서는 DB/사내 API 구현으로 교체한다."""
    return FileSpecRepository(settings.fixture_dir)


SpecRepositoryDep = Annotated[SpecRepository, Depends(get_spec_repository)]
