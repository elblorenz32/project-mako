import os

from core.agent import Agent
from core.common import InvalidConfigurationError
from core.config import get_config
from core.logger import Logger


def initialize():
	logger = Logger("main")

	logger.info("Initializing...")
	logger.info(f"HF_HUB_DISABLE_XET={os.environ.get('HF_HUB_DISABLE_XET')}")
	try:
		logger.info("Loading configuration...")
		settings = get_config()
		logger.info("Configuration loaded.")
		logger.debug("Found the following settings:", value=settings)
	except InvalidConfigurationError as e:
		logger.error("Failed to load configuration during startup.", exception=e)
		exit(1)

	agent = Agent()

	agent.run()

if __name__ == "__main__":
	initialize()