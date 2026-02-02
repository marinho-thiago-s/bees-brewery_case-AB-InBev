"""Bronze layer schemas - Raw data from API"""

from pyspark.sql.types import StructType, StructField, StringType, IntegerType, TimestampType


class BronzeSchema:
    """Data contracts for Bronze layer (raw ingested data)"""
    
    BREWERIES_SCHEMA = StructType([
        StructField("id", StringType(), True),
        StructField("name", StringType(), False),
        StructField("brewery_type", StringType(), True),
        StructField("address_1", StringType(), True),
        StructField("address_2", StringType(), True),
        StructField("address_3", StringType(), True),
        StructField("city", StringType(), True),
        StructField("state_province", StringType(), True),
        StructField("postal_code", StringType(), True),
        StructField("country", StringType(), True),
        StructField("county_province", StringType(), True),
        StructField("phone", StringType(), True),
        StructField("website_url", StringType(), True),
        StructField("updated_at", StringType(), True),
        StructField("created_at", StringType(), True),
    ])


# Exportar schema para uso direto em imports
BRONZE_SCHEMA = BronzeSchema.BREWERIES_SCHEMA
