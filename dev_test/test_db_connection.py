import psycopg2

conn = psycopg2.connect(
    host="35.209.14.79",
    database="ml_platform",
    user="ml_playground",
    password="ml_playground@123",
    port=5432
)

print("Connected successfully!")