import os
from pathlib import Path
from huggingface_hub import hf_hub_download


def ensure_model_path(
		repo_id_or_name: str,
		filename: str | None = None,
		local_dir: str | Path | None = None
) -> str:
	"""
	Returns the path to a model. If given a Hugging Face repo, downloads
	the model file if not locally cached and returns its absolute path.

	Examples:
		# Standard model name (returns 'tiny' as-is)
		ensure_model_path("tiny")

		# Local file path (returns absolute path if file exists)
		ensure_model_path("./models/ggml-tiny.bin")

		# Hugging Face GGML / model file
		ensure_model_path("ggerganov/whisper.cpp", "ggml-tiny.bin")
	"""
	# 1. Check if it's already a local file path
	if os.path.exists(repo_id_or_name):
		return str(Path(repo_id_or_name).resolve())

	# 2. If a filename is provided, fetch/cache from Hugging Face Hub
	if filename:
		file_path = hf_hub_download(
			repo_id=repo_id_or_name,
			filename=filename,
			local_dir=local_dir  # Optional: force download to a specific folder instead of HF cache
		)
		return str(Path(file_path).resolve())

	# 3. Fallback: standard model string (e.g. "tiny", "base.en")
	return repo_id_or_name