import os

class Settings:
    DATABASE_URL = os.getenv("DATABASE_URL", "mysql+pymysql://root:root@localhost/medical_db")
    # DATABASE_URL = "mysql+pymysql://root:root@host.docker.internal:3306/medical_db"
settings = Settings()



