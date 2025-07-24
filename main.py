from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse,RedirectResponse
from database import engine, SessionLocal, Base
from models import User

#Create the database tables
Base.metadata.create_all(bind=engine)

#Calling the FastAPI creating an instance app
app = FastAPI()


#For knowing the Templates Directory for getting all the Templates Files
templates = Jinja2Templates(directory="templates")


@app.get("/", response_class=HTMLResponse)
def root(request: Request):
    return templates.TemplateResponse(request=request, name="login.html")


        
        
        
        