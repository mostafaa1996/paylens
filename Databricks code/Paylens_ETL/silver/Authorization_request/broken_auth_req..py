from pyspark import pipelines as dp
from pyspark.sql.dataframe import DataFrame
from pyspark.sql.functions import col
from pyspark.sql import functions as F

@dp.table(
name="paylensdatabricks.silver.broken_auth_req"
,comment="Broken Authorization events stored in silver layer"
)

def auth_req() -> DataFrame:
  return (
      spark.readStream.table("auth_req_validated")
                .filter(F.size(col("violations_array")) > 0)
  )