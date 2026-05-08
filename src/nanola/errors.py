class NanolaError(Exception):
    """Base class for expected Nanola failures."""


class DependencyMissingError(NanolaError):
    pass


class ConfigurationError(NanolaError):
    pass
