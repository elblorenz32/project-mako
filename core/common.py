class InvalidConfigurationError(Exception):
	"""
	Exception raised when configuration is invalid and unusable.
	"""
	def __init__(self, message: str, original: Exception):
		super().__init__(message)
		self.original = original