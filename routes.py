# from fastapi import FastAPI, Depends, HTTPException, Request
# from main import *
# from schemas import UserCreate, UserLogin
# from models import User
# from database import SessionLocal
# from sqlalchemy.orm import Session
# from fastapi.templating import Jinja2Templates
# from auth import hash_password, verify_password,create_token

# @app.post("/register", response_class=HTMLResponse)
# def register(request: Request,user: UserCreate, db: Session = Depends(get_db)):
#     existing = db.query(User).filter(User.email== user.email).first()
#     if existing:
#         raise HTTPException(status_code=400, detail="Email Already Registered!")
#     hashed_pw = hash_password(user.password)
#     new_user = User(name = user.name, email=user.email, password_hash = hashed_pw, role=user.role)
#     db.add(new_user)
#     db.commit()
#     return templates.TemplateResponse("register.html",{"request": request, "message": "User registered successfully!"})



# @app.post("/login", response_class=HTMLResponse)
# def login(request: Request, user: UserLogin, db: Session = Depends(get_db)):
#     db_user = db.query(User).filter(User.email == user.email).first()
#     if not db_user or not verify_password(user.password, db_user.password_hash):
#         raise HTTPException(status_code=401, detail="Invalid Credentials")
#     token = create_token({"sub": db_user.email})
#     # return {"access_token": token, "token_type": "bearer"}
#     return templates.TemplateResponse("register.html",{"request": request, "message": "User registered successfully!"})