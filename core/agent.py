import json
import sys
from enum import Enum, auto
from pathlib import Path
from time import sleep

from mpmath.libmp import trailing
from ollama import ChatResponse, chat, ResponseError

from core.config import get_config
from core.logger import Logger, logger
from voice.speech_to_text import STTHandler


class AgentState(Enum):
	IDLE = auto()  # Listening/waiting for input
	PROCESSING = auto()  # Generating text response with Ollama
	SPEAKING = auto()  # Playing TTS audio (for future TTS implementation)


class Agent:
	_initialized = False

	def __init__(self):
		if not Agent._initialized:
			self.logger = Logger("agent")
			self.stt = None
			self.state = AgentState.IDLE
			self.interrupt_requested = False

			self._setup()
			Agent._initialized = True

	def _setup(self):
		self._config = get_config().agent

		personality_file = self._config.PERSONALITY_FILE
		if not personality_file:
			self.logger.error("Could not parse personality file: ", value=personality_file)
			raise AssertionError("Could not parse personality file")
		personality_file = Path(personality_file)
		if not personality_file.exists():
			self.logger.error("Personality file does not exist: ", value=personality_file)
			raise FileNotFoundError("Personality file does not exist", personality_file)

		self.personality = json.load(open(personality_file))

		traits: list[str] = self.personality.get("traits")
		if not traits:
			self.logger.error("Could not parse traits: ", value=traits)
			raise ValueError("Traits are empty!")
		self.system_message = (
			f"Du bist ein jüngeres Mädchen namens {self.personality.get('name', '')}. "
			f"Dein charakter ist {", ".join(traits[:-1]) + (" und " if len(traits) > 1 else "") + traits[-1]}. "
			f"Dein Gesprächsstil ist eher {self.personality.get('speaking_style', 'normal')}. "
			f"Deine Antwortlänge ist eher {self.personality.get('answer_length', 'normal')}. "
			"Du bist mit {user} einigermaßen vertraut. Ihr duzt euch. "
			"Antworte in gesprochenem Text. "
			"Wenn ein Wort ein Fachwort ist, verwende das originale Wort in der Fachsprache."
		)
		self.logger.debug("System prompt: ", value=self.system_message)

		# Initialize STT with interrupt trigger callback
		self.stt = STTHandler(
			logger=self.logger,
			on_speech_start=self._handle_user_speech_started
		)

	def _handle_user_speech_started(self):
		"""
		Callback fired immediately by STT as soon as user begins speaking.
		Prepared for future interrupt handling.
		"""
		if self.state in (AgentState.PROCESSING, AgentState.SPEAKING):
			self.logger.info("Interrupt detected! User began speaking while agent was busy.")
			self.interrupt_requested = True
		# FUTURE TTS: Stop audio playback immediately here
		# self.tts.stop()

	def run(self):
		self.stt.start()
		self.logger.info("Agent event loop started.")

		try:
			while True:
				# ----------------------------------------------------
				# STATE 1: IDLE / LISTENING
				# ----------------------------------------------------
				if self.state == AgentState.IDLE:
					user_prompt = self.stt.get_transcript()
					if user_prompt:
						self.logger.debug(f"User said: {user_prompt}")
						self.interrupt_requested = False
						self.state = AgentState.PROCESSING

				# ----------------------------------------------------
				# STATE 2: PROCESSING (Ollama)
				# ----------------------------------------------------
				elif self.state == AgentState.PROCESSING:
					try:
						response: ChatResponse = chat(
							model=self._config.MODEL,
							messages=[
								{"role": "system", "content": self.system_message},
								{"role": "user", "content": user_prompt}
							],
							think=False,
							stream=False,
							options={"temperature": 1}
						)

						if self.interrupt_requested:
							self.logger.info("Ollama response discarded due to interrupt.")
							self.state = AgentState.IDLE
							continue

						response_text = response.message.content
						self.logger.info(f"Agent response: {response_text}")
						self.state = AgentState.SPEAKING

					except ResponseError as e:
						self.logger.error("Could not generate response: ", value=e)
						self.state = AgentState.IDLE

				# ----------------------------------------------------
				# STATE 3: SPEAKING (TTS Output)
				# ----------------------------------------------------
				elif self.state == AgentState.SPEAKING:
					if self.interrupt_requested:
						self.logger.info("Speech interrupted by user.")
						self.stt.clear_queue()

					self.state = AgentState.IDLE

				sleep(0.05)

		except KeyboardInterrupt:
			self.logger.info("Keyboard interrupt received.")
		finally:
			self.logger.info("Shutting down STT and exiting...")
			if self.stt:
				self.stt.stop()
			self.logger.info("Agent stopped completely.")