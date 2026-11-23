from pyspark import pipelines as dp
from pyspark.sql.dataframe import DataFrame
from pyspark.sql.functions import col
from pyspark.sql import functions as F


@dp.temporary_view(name="auth_req_validated")
def auth_req_validated() -> DataFrame:
    def present(name):
        c = F.col(name)
        return c.isNotNull() & (F.trim(c) != "")

    schema = """
      schema_version INT,
      event_id STRING,
      event_type STRING,
      event_time TIMESTAMP,
      source STRING,
      payment_id STRING,
      attempt_id STRING,
      merchant_id STRING,
      order_reference STRING,
      requested_amount_minor LONG,
      currency STRING,
      channel STRING,
      payment_method STRUCT<
          type: STRING,
          token: STRING,
          card_presence: STRING,
          entry_mode: STRING
      >,
      terminal_id STRING,
      ip_address STRING,
      idempotency_key STRING
    """
    # extract the payload from the raw events
    events_payloads = (spark.readStream.table("paylensdatabricks.bronze.raw_events")
                .select(F.col("paylens_payload"))
          )
    
    #creating event_type column
    events_payloads = events_payloads.withColumn(
        "event_type",
        F.get_json_object(F.col("paylens_payload"), "$.event_type")
    )
    
    # filter for the authorization_requested events
    events_payloads = events_payloads.filter(col("event_type") == "authorization_requested")
    
    # select the column of payload and convert its type from json to struct based on the schema
    # and rename the column to payload
    events_payloads = events_payloads.select(F.from_json(col("paylens_payload"), schema).alias("payload"))

    #select columns from the struct based on the schema
    events_payloads = events_payloads.select("payload.*")
    events_payloads = events_payloads.select("*" , "payment_method.*").drop("payment_method")
    events_payloads = events_payloads.withColumnRenamed("token" , "payment_token")

    # adding 1 additional column for the violations
    parsed = events_payloads.withColumn("violations_array" , F.lit(None).cast("array<string>"))

    # read merchants and tokens from our reference tables
    merchants = (spark.read.table(
        "paylensdatabricks.reference.merchants"
    ).select(F.col("merchant_id")).distinct().alias("Merchant_IDs"))

    tokens = (spark.read.table(
        "paylensdatabricks.reference.customer_payment_methods"
    ).select("payment_token").distinct().alias("Tokens"))

    parsed = parsed.join(merchants , on= (parsed.merchant_id == merchants.Merchant_IDs) , how= "left")
    parsed = parsed.join(tokens , on= (parsed.payment_token == tokens.Tokens), how= "left")
     
    validated = parsed.withColumn(
        "violations_array",
            F.array_compact(F.array(
                F.when(~present("merchant_id"), "merchant_id is missing"),
                F.when(present("merchant_id") & (parsed.Merchant_IDs.isNull()), "unknown merchant"),
                F.when(~present("payment_token") , "payment_token is missing"),
                F.when(present("payment_token") & (parsed.Tokens.isNull()), "unknown payment token"),
                F.when(~present("schema_version") , "schema_version is missing"),
                F.when(present("schema_version") & (col("schema_version") != 1), "schema_version is not 1"),
                F.when(~present("event_id") , "event_id is missing"),
                F.when(~present("event_type") , "event_type is missing"),
                F.when(col("event_time").isNull(), "event_time is missing or invalid"),
                F.when(~present("source") , "source is missing"),
                F.when(present("source") & ~(col("source").isin("backend" , "webhook")) , "source is not backend or webhook"),
                F.when(~present("payment_id") , "payment_id is missing"),
                F.when(~present("attempt_id") , "attempt_id is missing"),
                F.when(~present("order_reference") , "order_reference is missing"),
                F.when(~present("requested_amount_minor") , "requested_amount_minor is missing"),
                F.when(present("requested_amount_minor") & ~(col("requested_amount_minor") > 0) , "requested_amount_minor is not positive"),
                F.when(~present("currency") , "currency is missing"),
                F.when(present("currency") & ~(col("currency").isin("USD" , "EUR" , "EGP")) , "currency is not USD, EUR or EGP"),
                F.when(~present("channel") , "channel is missing"),
                F.when(present("channel") & ~(col("channel").isin("web" , "pos" , "mobile")) , "channel is not online, pos or mobile"),
                F.when(~present("type") , "type is missing"),
                F.when(~present("card_presence") , "card_presence is missing"),
                F.when(present("card_presence") & ~(col("card_presence").isin("CP" , "CNP")) , "card_presence is not CP or CNP"),
                F.when(~present("payment_method.entry_mode") , "payment_method.entry_mode is missing"),
                F.when(present("payment_method.entry_mode") & ~(col("payment_method.entry_mode").isin("online" , "offline")) , "payment entry_mode is not MS or IC"),                
                F.when((col("channel") == "pos") & (~present("terminal_id") | (col("terminal_id").isNull())) , "terminal_id is missing"),
                F.when((col("channel") == "web") & (~present("ip_address") | (col("ip_address").isNull())) , "ip_address is missing"),
                F.when(~present("idempotency_key") , "idempotency_key is missing") 
            ))
    )

    return validated.drop("Merchant_IDs", "Tokens")


    



