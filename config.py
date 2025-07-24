import os

class Settings:
    DATABASE_URL = os.getenv("DATABASE_URL", "mysql+pymysql://root:root@localhost/medical_db")
settings = Settings()




# import os
# from dotenv import load_dotenv

# load_dotenv()              # Load environment variable from .env file

# class Settings:
#     DATABASE_URL = os.getenv("DATABASE_URL","mysql+pymysql://root:root@localhost/medical_db;")
#     SECRET_KEY = os.getenv("SECRET_KEY", "KEY")
#     ALGORITHM = "HS256"
#     ACCESS_TOKEN_EXPIRE_MINUTES = 60
    
    
# settings = Settings()