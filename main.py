from datetime import datetime
from fastapi import FastAPI, Depends, HTTPException, Request, Form
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse,RedirectResponse
from database import engine, SessionLocal, Base
from sqlalchemy.orm import Session
from models import User, DoctorSchedule, Appointment
from auth import hash_password, verify_password,create_token, SECRET_KEY, ALGORITHM
from jose import JWTError, jwt
from schemas import UserCreate, UserLogin
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse

#Create the database tables
Base.metadata.create_all(bind=engine)

#Calling the FastAPI creating an instance app
app = FastAPI()

#For knwoing the static Directory for getting all the static Files
app.mount("/static", StaticFiles(directory="static"), name="static")


#For knowing the Templates Directory for getting all the Templates Files
templates = Jinja2Templates(directory="templates")

#For Creating Session opening and Closing the Database
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


#For Creating current user
def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    token = request.cookies.get("access_token")
    print(token,'etyhrtenfhefdnbghgchgc')
    if not token:
        raise HTTPException(status_code=401, detail="Token missing")

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email = payload.get("sub")
        if email is None:
            raise HTTPException(status_code=401, detail="Invalid token")
    except JWTError:
        raise HTTPException(status_code=401, detail="Token decode error")

    user = db.query(User).filter(User.email == email).first()
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")

    return user
 

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
    confirm_password: str = Form(...),
    role: str = Form(...), db: Session = Depends(get_db)):

    if password != confirm_password:
        return templates.TemplateResponse("register.html", {
            "request": request,
            "error": "Passwords do not match!"
        })

    
    # ✅ Create a Pydantic model instance using form data
    user = UserCreate(name=name, email=email, password=password, role=role)
    existing = db.query(User).filter(User.email == user.email).first()
    if existing:
        return templates.TemplateResponse("register.html", {
            "request": request,
            "error": "Email already registered!"
        })
    hashed_pw = hash_password(user.password)
    new_user = User(name = user.name, email=user.email, password_hash = hashed_pw, role=user.role)
    db.add(new_user)
    db.commit()
    
     # ✅ Redirect to login page
    return RedirectResponse(url="/login", status_code=303)



@app.get("/login", response_class=HTMLResponse)
async def login(request: Request):
    return templates.TemplateResponse("login.html",{"request": request, "success": "User registered successfully!"})
    

@app.post("/login", response_class=HTMLResponse)
async def login(request: Request,
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)):
    
    # ✅ Create a Pydantic model instance using form data
    user = UserLogin(email=email, password=password)
    db_user = db.query(User).filter(User.email == user.email).first()
    if not db_user or not verify_password(user.password, db_user.password_hash):
        return templates.TemplateResponse("login.html",{"request": request, "error": "Invalid Credentials"})
    token = create_token({"sub": db_user.email})
    response = templates.TemplateResponse("dashboard.html", {"request": request, "user": db_user, "error": "Invalid Credentials"})
    response.set_cookie(key="access_token", value=token, httponly=True, secure=False)  # Use secure=True in production
    return response
    # print(token,'ueywewhdhehjer')
    # print(db_user.email,"wudhudyuhdjydudhydchgcgchbc")
    
    # return {"access_token": token, "token_type": "bearer"}
    # return templates.TemplateResponse("dashboard.html",{"request": request, "user": db_user, "success": "Login successful!"})


@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request,db: Session = Depends(get_db)):
    # token = request.cookies.get("access_token")
    # if not token:
    #     return RedirectResponse("/login")
    user = get_current_user(request,db)
    
    return templates.TemplateResponse("dashboard.html",{"request": request, "user": user,"success": "Login successful!"})

@app.get("/doctor/schedule", response_class=HTMLResponse)
def schedule_form(request:Request):
    return templates.TemplateResponse("doctor_schedule.html", {"request": request})

@app.post("/doctor/schedule")
def schedule_post(
    request:Request, 
    date: str=Form(...),
    start_time: str=Form(...),
    end_time: str=Form(...),
    db: Session = Depends(get_db)
    ):
    # token = request.cookies.get("access_token")
    current_user = get_current_user(request, db)
    if current_user.role != "doctor":
        raise HTTPException(status_code=403, detail= "Not Authorized")
    
    new_schedule = DoctorSchedule(
        doctor_id = current_user.id,
        date = datetime.strptime(date, "%Y-%m-%d").date(),
        start_time = datetime.strptime(start_time, "%H:%M").time(),
        end_time=datetime.strptime(end_time, "%H:%M").time()
    )
    
    db.add(new_schedule)
    db.commit()
    return RedirectResponse("/dashboard", status_code=303)
    
        
@app.get("/appointments", response_class=HTMLResponse)
def appointment_form(request: Request):
    return templates.TemplateResponse("book_appointment.html", {"request": request})

@app.post("/appointments")
def appointment_post(
    request: Request,
    doctor_id: int = Form(...),
    date: str = Form(...),
    time: str = Form(...),
    db: Session = Depends(get_db)
):
    token = request.cookies.get("access_token")
    current_user = get_current_user(token, db)
    if current_user.role != "patient":
        raise HTTPException(status_code=403, detail="Not authorized")

    schedule = db.query(DoctorSchedule).filter(
        DoctorSchedule.doctor_id == doctor_id,
        DoctorSchedule.date == datetime.strptime(date, "%Y-%m-%d").date()
    ).first()

    if not schedule:
        return templates.TemplateResponse("book_appointment.html", {"request": request, "msg": "Doctor not available"})

    new_appointment = Appointment(
        patient_id=current_user.id,
        doctor_id=doctor_id,
        date=datetime.strptime(date, "%Y-%m-%d").date(),
        time=datetime.strptime(time, "%H:%M").time(),
        status="booked"
    )
    db.add(new_appointment)
    db.commit()
    return RedirectResponse("/dashboard", status_code=303)  


@app.get("/logout")
def logout(request: Request, db: Session= Depends(get_db)):
    return templates.TemplateResponse("login.html",{"request": request})