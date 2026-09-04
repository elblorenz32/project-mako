import atexit
import logging
import logging.handlers
import queue
import sys
from pathlib import Path
from typing import Any

from core.config import get_config


class StructuredFormatter(logging.Formatter):
	"""
	Human-readable formatter with structured metadata support.
	"""

	def format(self, record: logging.LogRecord) -> str:
		timestamp = self.formatTime(record)

		message = (
			f"{timestamp} "
			f"[{record.levelname}] "
			f"{record.name}: "
			f"{record.getMessage()}"
		)

		# Append structured metadata
		extras = {
			key: value
			for key, value in record.__dict__.items()
			if key not in {
				"name",
				"msg",
				"message",
				"taskName",
				"args",
				"levelname",
				"levelno",
				"pathname",
				"filename",
				"module",
				"exc_info",
				"exc_text",
				"stack_info",
				"lineno",
				"funcName",
				"created",
				"msecs",
				"relativeCreated",
				"thread",
				"threadName",
				"process",
				"processName",
			}
		}

		if extras:
			if extras["value"]:
				message += f"{extras['value']}"
			else:
				message += f" | {extras}"

		return message


class LoggerFactory:
	"""
	Application logger factory.

	Supports:
	- structured metadata
	- console output
	- file output
	- async-friendly queue logging
	"""

	_initialized = False
	_listener = None

	@classmethod
	def setup(cls):
		if cls._initialized:
			return

		config = get_config()
		level = config.logger.LOG_LEVEL

		formatter = StructuredFormatter(
			"%(asctime)s [%(levelname)-8s] %(name)-s : %(message)s"
		)

		console = logging.StreamHandler(sys.stdout)
		console.setFormatter(formatter)

		file = logging.handlers.RotatingFileHandler(
			filename=Path(config.logger.LOG_FILE),
			encoding="utf-8",
			mode="a",
			maxBytes=config.logger.MAX_LOG_SIZE,
			backupCount=5,
		)
		file.setFormatter(formatter)
		file.doRollover()

		log_queue = queue.Queue(-1)

		listener = logging.handlers.QueueListener(
			log_queue,
			console,
			file,
		)
		listener.start()

		root = logging.getLogger()
		root.setLevel(level)
		root.addHandler(logging.handlers.QueueHandler(log_queue))

		cls._listener = True
		cls._initialized = True

		atexit.register(listener.stop)

	@classmethod
	def get_logger(cls, name):
		cls.setup()
		logging.getLogger("faster_whisper").setLevel(logging.WARNING)
		logging.getLogger("httpx").setLevel(logging.WARNING)
		logging.getLogger("RealtimeSTT.safepipe").setLevel(logging.INFO)
		return logging.getLogger(name)

class Logger:

	def __init__(self, name: str = None):
		self._logger = LoggerFactory.get_logger(name)

	def info(self, event: str, **kwargs: Any):
		self._logger.info(event, extra=kwargs)

	def debug(self, event: str, **kwargs: Any):
		self._logger.debug(event, extra=kwargs)

	def warning(self, event: str, **kwargs: Any):
		self._logger.warning(event, extra=kwargs)

	def error(self, event: str, **kwargs: Any):
		self._logger.error(event, extra=kwargs)

	def exception(self, event: str, **kwargs: Any):
		self._logger.exception(event, extra=kwargs)


logger = Logger()