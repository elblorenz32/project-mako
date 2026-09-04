import os
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, ValidationError, BaseModel
from pydantic_settings import BaseSettings, SettingsConfigDict

from core.common import InvalidConfigurationError


# noinspection PyArgumentList
class LoggerConfig(BaseModel):
	"""
	Logger configuration.
	"""

	model_config = SettingsConfigDict(
		case_sensitive=True,
		validate_default=True,
		extra="ignore",
		frozen=True,
	)

	LOG_LEVEL: Literal[
		"DEBUG",
		"INFO",
		"WARNING",
		"ERROR",
		"CRITICAL",
		"FATAL",
	] = Field(
		"INFO",
		description="Minimum Log level. Default: INFO",
	)

	LOG_FILE: str = Field(
		"logs/log.txt",
		description="Log file path. Default: logs/log.txt",
	)

	MAX_LOG_SIZE: int = Field(
		1024 * 1024 * 5,
		gt=0,
		description="Maximum log file size in bytes. Default: 5MB",
	)


# noinspection PyArgumentList
class AgentConfig(BaseModel):
	"""
	Agent configuration.
	"""

	model_config = SettingsConfigDict(
		case_sensitive=True,
		validate_default=True,
		extra="ignore",
		frozen=True,
	)

	PERSONALITY_FILE: str = Field(
		"personality/profile.json",
		description="Personality file path. Default: personality/profile.json",
	)

	MODEL: str = Field(
		...,
		description="Ollama model",
	)


# noinspection PyArgumentList
class Config(BaseSettings):
	"""
	Application configuration.

	Priority:
	1. Environment variables
	2. .env file
	3. Default values
	"""

	# region Required environment variables

	# endregion

	# region Optional environment variables

	# endregion

	# region Extensions

	# endregion

	logger: LoggerConfig = Field(
		default_factory=LoggerConfig
	)

	agent: AgentConfig = Field(
		default_factory=AgentConfig
	)

	model_config = SettingsConfigDict(
		env_file=os.getenv("ENV_FILE", ".env"),
		env_file_encoding="utf-8",
		env_nested_delimiter=".",
		case_sensitive=True,
		validate_default=True,
		extra="ignore",
		frozen=True,
	)


@lru_cache
def get_config() -> Config | None:
	"""
	Cached configuration instance.
	"""
	try:
		return Config()
	except ValidationError as e:
		raise InvalidConfigurationError("Invalid application configuration", e) from e