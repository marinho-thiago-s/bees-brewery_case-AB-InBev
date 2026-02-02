"""Custom exceptions hierarchy for Bees Brewery pipeline"""


class BeesBreweryException(Exception):
    """Base exception for all Bees Brewery errors"""
    pass


class DataQualityException(BeesBreweryException):
    """Raised when data quality validation fails"""
    pass


class StorageException(BeesBreweryException):
    """Raised when storage operations fail"""
    pass


class SparkJobException(BeesBreweryException):
    """Raised when Spark job execution fails"""
    pass


class ConfigurationException(BeesBreweryException):
    """Raised when configuration is invalid"""
    pass
