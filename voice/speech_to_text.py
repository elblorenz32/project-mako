import queue
import threading
import sounddevice
from RealtimeSTT import AudioToTextRecorder

from voice.model_loader import ensure_model_path

sounddevice.sleep(1) # Convince pycharm that it is necessary. Simply importing sounddevice stops asla errors

class STTHandler:
	def __init__(self, logger=None, on_speech_start=None, model_spec="tiny", hf_filename=None):
		self.logger = logger
		self.on_speech_start = on_speech_start
		self.transcript_queue = queue.Queue()

		# Resolve model path or name (downloads from HF if needed)
		# self.model_path = ensure_model_path(model_spec, filename=hf_filename)
		self.model_path = ensure_model_path("TheChola/whisper-large-v3-turbo-german-faster-whisper")

		self._recorder = None
		self._is_running = False
		self._worker_thread = None

	def _on_recording_start(self):
		if self.logger:
			self.logger.debug("STT: User started speaking...")
		if self.on_speech_start:
			self.on_speech_start()

	def start(self):
		if self._is_running:
			return

		if self.logger:
			self.logger.info("Initializing RealtimeSTT recorder...")

		self._recorder = AudioToTextRecorder(
			transcription_engine="faster-whisper",
			on_recording_start=self._on_recording_start,
			initial_prompt="Common names and words: Mako, miau, shutdown",
			spinner=False,
			language="de",
			model=self.model_path
		)

		self._is_running = True
		self._worker_thread = threading.Thread(target=self._listen_loop, daemon=True)
		self._worker_thread.start()

		if self.logger:
			self.logger.info("STT Handler started.")

	def _listen_loop(self):
		while self._is_running:
			try:
				# recorder.text() blocks internally until a phrase ends
				text: str = self._recorder.text()
				if text and text.strip():
					clean_text = text.strip()
					if self.logger:
						self.logger.debug(f"STT Transcribed: {clean_text}")
					if clean_text.lower().startswith("shutdown"):
						self.logger.warning("'shutdown' command received'")
						self.stop()
						raise KeyboardInterrupt("'shutdown' command received'")
					self.transcript_queue.put(clean_text)
			except Exception as e:
				# If abort() or shutdown() was called, break out cleanly
				if not self._is_running:
					break
				if self.logger:
					self.logger.error(f"Error in STT listen loop: {e}")

	def get_transcript(self) -> str | None:
		try:
			return self.transcript_queue.get_nowait()
		except queue.Empty:
			return None

	def clear_queue(self):
		with self.transcript_queue.mutex:
			self.transcript_queue.queue.clear()

	def stop(self):
		"""Cleanly aborts and shuts down RealtimeSTT without hanging."""
		if not self._is_running:
			return

		self._is_running = False

		if self._recorder:
			try:
				# 1. Abort immediately to break out of blocking recorder.text()
				if hasattr(self._recorder, "abort"):
					self._recorder.abort()

				# 2. Terminate PyAudio streams and internal worker processes
				if hasattr(self._recorder, "shutdown"):
					self._recorder.shutdown()
			except Exception as e:
				if self.logger:
					self.logger.error(f"Error during STT shutdown: {e}")
			finally:
				self._recorder = None

		# 3. Join worker thread with timeout as a safety fallback
		if self._worker_thread and self._worker_thread.is_alive():
			self._worker_thread.join(timeout=1.0)