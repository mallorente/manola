class ManolaError(Exception):
    """Base class for expected Manola failures."""


class DependencyMissingError(ManolaError):
    pass


class ConfigurationError(ManolaError):
    pass
