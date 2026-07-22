"""환경 설정.

폐쇄망 이식을 전제로 하므로 기본값만으로도 로컬에서 동작해야 한다.
환경변수는 `SRE_` 접두사를 쓴다. 단 배포 플랫폼이 관례적으로 쓰는 이름
(`CORS_ORIGINS`)은 접두사 없이 그대로 읽는다.

**모든 값은 런타임에 읽는다.** 빌드 타임에 굳는 값이 없어야
이미지 하나를 dev → stg → prd 로 승격할 수 있다 (docs/open-questions.md #35).
"""

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="SRE_", env_file=".env")

    app_name: str = "swagger-rag-eval API"
    version: str = "0.1.0"

    # 대시보드(프론트) 출처. 콤마로 구분한다. 예: https://a.example.com,https://b.example.com
    #
    # 문자열로 받아서 직접 쪼갠다. pydantic-settings 는 list 타입 필드를 환경변수에서
    # 읽을 때 JSON 으로 파싱하려 들기 때문에, 콤마 구분 문자열을 주면 터진다.
    cors_origins_raw: str = Field(
        default="http://localhost:3000",
        validation_alias="CORS_ORIGINS",
    )

    # 평가 대상 API. Phase 2 부터 openapi.json 을 여기서 가져온다.
    sample_api_base_url: str = "http://localhost:8001"

    # 로컬 저장소가 읽는 디렉토리. 사내에서 DB 어댑터로 갈아끼우면 쓰이지 않는다.
    fixture_dir: Path = Path(__file__).resolve().parents[1] / "fixtures"

    # /ready 가 존재를 확인할 평가 결과. 데이터 소스가 실제로 읽히는지 보는 용도다.
    readiness_trace_id: str = "A492"

    @property
    def cors_origins(self) -> list[str]:
        """콤마 구분 문자열을 목록으로. 빈 항목과 앞뒤 공백은 버린다."""
        return [origin.strip() for origin in self.cors_origins_raw.split(",") if origin.strip()]


settings = Settings()
