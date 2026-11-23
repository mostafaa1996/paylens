from pyspark import pipelines as dp
from pyspark.sql.dataframe import DataFrame
from pyspark.sql.functions import col
from pyspark.sql import functions as F

@dp.table(
name="paylensdatabricks.bronze.raw_events"
,comment="Raw transactions data or refunds from the paylens App"
)

def raw_bronze() -> DataFrame:
    dp = (spark.readStream.format("kafka")
                    .option("kafka.bootstrap.servers", "EventsIngestion.servicebus.windows.net:9093") # -Host Name of Azure Event Hub is: EventsIngestion.servicebus.windows.net & Event hub Port in Kafka is 9093
                    .option("subscribe", "auth_req") #topic name
                    .option("databricks.serviceCredential", "credential_paylens_stream") #service credential name to connect with Access control for Azure databricks which has role of Event Hub receiver
                    .option("startingOffsets", "latest")
                    .load()
                    .select(
                        F.col("value").cast("string").alias("paylens_payload"),
                        "topic",
                        "partition",
                        "offset",
                        F.col("timestamp").alias("message_time"),
                    ))
    return dp
                    

