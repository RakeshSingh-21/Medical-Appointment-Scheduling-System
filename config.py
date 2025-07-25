import os

class Settings:
    DATABASE_URL = os.getenv("DATABASE_URL", "mysql+pymysql://root:root@localhost/medical_db")
settings = Settings()




