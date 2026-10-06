from typing import Literal
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, model_validator


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    app_mode: Literal["local", "live"] = "local"
    viewer_key: str = ""
    analyst_key: str = ""
    admin_key: str = ""
    openai_api_key: str = ""
    openai_model: str = "gpt-4.1-mini"
    embedding_model: str = "text-embedding-3-small"
    pinecone_api_key: str = ""
    pinecone_host: str = ""
    pinecone_namespace: str = "demo-bank-v1"
    langsmith_tracing: bool = False
    langsmith_api_key: str = ""
    langsmith_project: str = "enterprise-assistant"
    token_capacity: int = Field(20, ge=1)
    token_refill_per_second: float = Field(0.2, gt=0)
    tool_timeout_seconds: float = Field(20, gt=0)
    mcp_enabled: bool = False

    @model_validator(mode="after")
    def validate_configuration(self):
        keys = [self.viewer_key, self.analyst_key, self.admin_key]
        if any(len(k) < 16 for k in keys) or len(set(keys)) != 3:
            raise ValueError("Set three distinct API keys of at least 16 characters in .env")
        if self.app_mode == "live":
            if not all([self.openai_api_key, self.pinecone_api_key,
                        self.pinecone_host, self.langsmith_api_key, self.langsmith_tracing]):
                raise ValueError("Live mode requires OpenAI, Pinecone and enabled LangSmith")
            if not self.pinecone_host.startswith("https://"):
                raise ValueError("Pinecone host must use HTTPS")
        return self
