from datetime import datetime
from fastapi import FastAPI, Depends, HTTPException, Request, Form
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse,RedirectResponse
from database import engine, SessionLocal, Base
from sqlalchemy.orm import Session
from models import User, DoctorSchedule, Appointment
from auth import hash_password, verify_password,create_token, SECRET_KEY, ALGORITHM
from jose import JWTError, jwt, ExpiredSignatureError
from schemas import UserCreate, UserLogin
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
from fastapi.requests import Request
from fastapi.exceptions import RequestValidationError
from fastapi import status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

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
    if not token:
        raise HTTPException(status_code=401, detail="Token missing")

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email = payload.get("sub")
        if email is None:
            raise HTTPException(status_code=401, detail="Invalid token")
    except ExpiredSignatureError:
        # Token expired
        raise HTTPException(status_code=401, detail="Token expired")
    except JWTError:
        raise HTTPException(status_code=401, detail="Token decode error")

    user = db.query(User).filter(User.email == email).first()
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")

    return user


@app.exception_handler(HTTPException)
async def auth_exception_handler(request: Request, exc: HTTPException):
    if exc.status_code == 401:
        return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)
    return Response(content=str(exc.detail), status_code=exc.status_code)

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
    prefix = "Dr." if user.role == "doctor" else "Pt." if user.role == "patient" else ""
    formatted_name = f"{prefix} {user.name}"
    new_user = User(name = formatted_name, email=user.email, password_hash = hashed_pw, role=user.role)
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
    response = RedirectResponse(url="/dashboard", status_code=303)
    response.set_cookie(key="access_token", value=token, httponly=True, secure=False)  # Use secure=True in production
    return response


@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request,db: Session = Depends(get_db)):
    user = get_current_user(request,db)
    context = {
        "request": request,
        "user": user,
        "success": "Login successful!"
    }

    if user.role == "doctor":
        context.update({
            "total_patients": db.query(Appointment).filter(Appointment.doctor_id == user.id).count(),
            "confirmed_bookings": db.query(Appointment)
                .filter(Appointment.doctor_id == user.id, Appointment.status == "confirmed")
                .count(),
            "upcoming_appointments": db.query(User.name.label("patient_name"),Appointment.date, Appointment.time, Appointment.status).join(User, User.id == Appointment.patient_id).filter(Appointment.doctor_id == user.id, Appointment.status == "confirmed").all()
        })  

    elif user.role == "patient":
        context.update({
            "my_bookings": db.query(Appointment).filter(Appointment.patient_id == user.id,Appointment.status == "confirmed").count(),
            "confirmed_appointments": db.query(User.name.label("doctor_name"),Appointment.date, Appointment.time, Appointment.status).join(User, User.id == Appointment.doctor_id).filter(Appointment.patient_id == user.id, Appointment.status == "confirmed").all(),
            "cancel_bookings": db.query(Appointment).filter(Appointment.patient_id == user.id,Appointment.status == "cancelled").count(),
                
        })
    return templates.TemplateResponse("dashboard.html", context)
           

@app.get("/doctor/schedule", response_class=HTMLResponse)
def schedule_form(request:Request,db: Session = Depends(get_db)):

    user = get_current_user(request, db)
    doctors = db.query(User).filter(User.role == "doctor").all()

    # fetch doctors list
    context = {
        "request": request,
        "user": user,
        "doctors": doctors,
    }

    if user.role == "doctor":
        context.update({
            "total_patients": db.query(Appointment).count(),
            "confirmed_bookings": db.query(Appointment)
                .filter(Appointment.doctor_id == user.id, Appointment.status == "confirmed")
                .count(),
            "upcoming_appointments": db.query(User.name.label("patient_name"),Appointment.date, Appointment.time, Appointment.status).join(User, User.id == Appointment.patient_id).filter(Appointment.doctor_id == user.id, Appointment.status == "confirmed").all()
        })

    elif user.role == "patient":
        context.update({
            
            "my_bookings": db.query(Appointment).filter(Appointment.patient_id == user.id,Appointment.status == "confirmed").count(),
            "confirmed_appointments": db.query(User.name.label("doctor_name"),Appointment.date, Appointment.time, Appointment.status).join(User, User.id == Appointment.doctor_id).filter(Appointment.patient_id == user.id, Appointment.status == "confirmed").all(),
            "cancel_bookings": db.query(Appointment).filter(Appointment.patient_id == user.id,Appointment.status == "cancelled").count(),
                
        })
    return templates.TemplateResponse("doctor_schedule.html",context)

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
    
    

@app.get("/appointment/{action}")
def appointment_form(
    action: str,
    request: Request,
    db: Session = Depends(get_db)
):
    user = get_current_user(request, db)
    if user.role != "patient":
        raise HTTPException(status_code=403, detail="Only patients can manage appointments")
    doctors = db.query(User).filter(User.role == "doctor").all()

    # fetch doctors list
    context = {
        "request": request,
        "action": action.capitalize(),
        "user": user,
        "doctors": doctors,
    }

    if user.role == "doctor":
        context.update({
            "total_patients": db.query(Appointment).count(),
            "confirmed_bookings": db.query(Appointment)
                .filter(Appointment.doctor_id == user.id, Appointment.status == "confirmed")
                .count(),
            "upcoming_appointments": db.query(User.name.label("patient_name"),Appointment.date, Appointment.time, Appointment.status).join(User, User.id == Appointment.patient_id).filter(Appointment.doctor_id == user.id, Appointment.status == "confirmed").all()
        })

    elif user.role == "patient":
        context.update({
            
            "my_bookings": db.query(Appointment).filter(Appointment.patient_id == user.id,Appointment.status == "confirmed").count(),
            "confirmed_appointments": db.query(User.name.label("doctor_name"),Appointment.date, Appointment.time, Appointment.status).join(User, User.id == Appointment.doctor_id).filter(Appointment.patient_id == user.id, Appointment.status == "confirmed").all(),
            "cancel_bookings": db.query(Appointment).filter(Appointment.patient_id == user.id,Appointment.status == "cancelled").count(),
                
        })
    return templates.TemplateResponse("book_appointment.html", context)


@app.post("/appointment/{action}")
def appointment_action(
    action: str,
    request: Request,
    doctor_id: int = Form(None),
    date: str = Form(None),
    slot: str = Form(None),
    appointment_id: str = Form(None),
    db: Session = Depends(get_db)
):
    user = get_current_user(request, db)
    if user.role != "patient":
        raise HTTPException(status_code=403, detail="Only patients can perform this action")

    if action.lower() == "book":
        new_appt = Appointment(
            patient_id=user.id,
            doctor_id=doctor_id,
            date=datetime.strptime(date, "%Y-%m-%d").date(),
            time=datetime.strptime(slot, "%H:%M").time(),
            status="pending"  # ✅ Set status here
        )
        db.add(new_appt)
        db.commit()
    elif action.lower() == "cancel":
        appt = db.query(Appointment).filter_by(id=appointment_id, patient_id=user.id).first()
        if not appt:
            raise HTTPException(status_code=404, detail="Appointment not found")
        db.delete(appt)
        db.commit()
    elif action.lower() == "reschedule":
        appt = db.query(Appointment).filter_by(patient_id=user.id, doctor_id=doctor_id, date=datetime.strptime(date, "%Y-%m-%d").date()).first()
        if not appt:
            raise HTTPException(status_code=404, detail="Original appointment not found")
        appt.time = datetime.strptime(slot, "%H:%M").time()
        db.commit()
    else:
        raise HTTPException(status_code=400, detail="Invalid action")

    return RedirectResponse("/dashboard", status_code=303)


@app.get("/appointments")
def view_appointments(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)

    if user.role == "doctor":
        appointments = (
            db.query(Appointment)
            .join(User, Appointment.patient_id == User.id)
            .filter(Appointment.doctor_id == user.id)
            .with_entities(Appointment.id, User.name.label("patient_name"), Appointment.date, Appointment.time, Appointment.status)
            .all()
        )
        return templates.TemplateResponse("appointments.html", {
            "request": request,
            "appointments": [{"id": a.id, "patient_name": a.patient_name, "doctor_name": user.name, "date": a.date, "time": a.time, "status": a.status} for a in appointments], "user": user
        })
        
    elif user.role == "patient":
        appointments = (
            db.query(Appointment)
            .join(User, Appointment.doctor_id == User.id)
            .filter(Appointment.patient_id == user.id)
            .with_entities(Appointment.id, User.name.label("doctor_name"), Appointment.date, Appointment.time, Appointment.status)
            .all()
        )
        return templates.TemplateResponse("appointments.html", {
            "request": request,
            "appointments": [{"id": a.id,"patient_name": user.name, "doctor_name": a.doctor_name, "date": a.date, "time": a.time,"status": a.status} for a in appointments], "user": user
        })
    else:
        raise HTTPException(status_code=403, detail="Unauthorized role")



@app.post("/appointments/{appointment_id}/confirm")
def confirm_appointment(appointment_id: int, request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if user.role != "doctor":
        raise HTTPException(status_code=403, detail="Only doctors can confirm appointments")

    appt = db.query(Appointment).filter_by(id=appointment_id, doctor_id=user.id).first()
    if not appt:
        raise HTTPException(status_code=404, detail="Appointment not found")

    appt.status = "confirmed"
    db.commit()
    return RedirectResponse("/appointments", status_code=303)


@app.post("/appointments/{appointment_id}/cancel")
def cancel_appointment(appointment_id: int, request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if user.role != "doctor":
        raise HTTPException(status_code=403, detail="Only doctors can cancel appointments")

    appt = db.query(Appointment).filter_by(id=appointment_id, doctor_id=user.id).first()
    if not appt:
        raise HTTPException(status_code=404, detail="Appointment not found")

    appt.status = "cancelled"
    db.commit()
    return RedirectResponse("/appointments", status_code=303)



@app.get("/view/schedule", response_class=HTMLResponse)
def doctor_schedule(request:Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    scheduled = db.query(DoctorSchedule).filter(DoctorSchedule.doctor_id == user.id).all()
    return templates.TemplateResponse("view_schedule.html", {"request": request, "user": user, "scheduled": scheduled})


@app.get("/logout")
def logout(request: Request, db: Session= Depends(get_db)):
    return RedirectResponse(url="/login", status_code=303)
