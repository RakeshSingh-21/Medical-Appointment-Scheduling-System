from fastapi import FastAPI, Depends, HTTPException, Request, Form
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse,RedirectResponse
from database import engine, SessionLocal, Base
from sqlalchemy.orm import Session
from models import User
from auth import hash_password, verify_password,create_token
from schemas import UserCreate, UserLogin
from fastapi.staticfiles import StaticFiles

#Create the database tables
Base.metadata.create_all(bind=engine)

#Calling the FastAPI creating an instance app
app = FastAPI()

#For knwoing the static Directory for getting all the static Files
app.mount("/static", StaticFiles(directory="static"), name="static")


#For knowing the Templates Directory for getting all the Templates Files
templates = Jinja2Templates(directory="templates")

#For Creating Session opeing and Closing the Database
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    return templates.TemplateResponse(request=request, name="login.html")

@app.get("/register", response_class=HTMLResponse)
async def register_form(request: Request):
    return templates.TemplateResponse("register.html", {"request": request})


@app.post("/register", response_class=HTMLResponse)
async def register(request: Request,  name: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    role: str = Form(...), db: Session = Depends(get_db)):
    
    # ✅ Create a Pydantic model instance using form data
    user = UserCreate(name=name, email=email, password=password, role=role)
    existing = db.query(User).filter(User.email== user.email).first()
    if existing:
        return templates.TemplateResponse("register.html", {
            "request": request,
            "error": "Email already registered!"
        })
    hashed_pw = hash_password(user.password)
    new_user = User(name = user.name, email=user.email, password_hash = hashed_pw, role=user.role)
    db.add(new_user)
    db.commit()
    return templates.TemplateResponse("register.html",{"request": request, "message": "User registered successfully!"})


@app.post("/login", response_class=HTMLResponse)
async def login(request: Request, user: UserLogin, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.email == user.email).first()
    if not db_user or not verify_password(user.password, db_user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid Credentials")
    token = create_token({"sub": db_user.email})
    # return {"access_token": token, "token_type": "bearer"}
    return templates.TemplateResponse("register.html",{"request": request, "message": "User registered successfully!"})


        
        
        
        