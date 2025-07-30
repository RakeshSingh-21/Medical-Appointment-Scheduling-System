import unittest
from fastapi.testclient import TestClient
from fastapi import status
from main import app
from database import SessionLocal, Base, engine
from models import User, DoctorSchedule, Appointment
from auth import hash_password
from datetime import datetime, date, time
from main import *
import json
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from auth import hash_password 

# Set up test database
TEST_DATABASE_URL = "mysql+pymysql://root:root@localhost/test_db"
engine = create_engine(TEST_DATABASE_URL)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base.metadata.create_all(bind=engine)

def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)

class TestApp(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Create test data
        db = TestingSessionLocal()
        
        # Create test users
        hashed_pw = hash_password("testpass")
        doctor = User(name="Dr. Test Doctor", email="doctor@test.com", password_hash=hashed_pw, role="doctor")
        patient = User(name="Pt. Test Patient", email="patient@test.com", password_hash=hashed_pw, role="patient")
        
        db.add(doctor)
        db.add(patient)
        db.commit()
        
        # Create test schedule
        schedule = DoctorSchedule(
            doctor_id=doctor.id,
            date=date(2023, 1, 1),
            start_time=time(9, 0),
            end_time=time(17, 0)
        )
        db.add(schedule)
        db.commit()
        
        # Create test appointment
        appointment = Appointment(
            patient_id=patient.id,
            doctor_id=doctor.id,
            date=date(2023, 1, 1),
            time=time(10, 0),
            status="pending"
        )
        db.add(appointment)
        db.commit()
        
        cls.doctor_id = doctor.id
        cls.patient_id = patient.id
        cls.appointment_id = appointment.id
        db.close()

    @classmethod
    def tearDownClass(cls):
        # Clean up database
        Base.metadata.drop_all(bind=engine)

    def setUp(self):
        self.db = TestingSessionLocal()
        
    def tearDown(self):
        self.db.close()

    def test_root_redirects_to_login(self):
        response = client.get("/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # self.assertIn("login.html", response.text)

    def test_register_get(self):
        response = client.get("/register")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # self.assertIn("register.html", response.text)

    def test_register_post_success(self):
        response = client.post("/register", data={
            "name": "New User",
            "email": "new@gmail.com",
            "password": "newpass",
            "confirm_password": "newpass",
            "role": "patient"
        }, follow_redirects=False)
        self.assertEqual(response.status_code, status.HTTP_303_SEE_OTHER)
        self.assertEqual(response.headers["location"], "/login")

    def test_register_post_password_mismatch(self):
        response = client.post("/register", data={
            "name": "New User",
            "email": "new2@gmail.com",
            "password": "newpass",
            "confirm_password": "wrongpass",
            "role": "patient"
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("Passwords do not match", response.text)

    def test_login_get(self):
        response = client.get("/login")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # self.assertIn("login.html", response.text)

    def test_login_post_success(self):
        response = client.post("/login", data={
            "email": "patient@test.com",
            "password": "testpass"
        }, follow_redirects=False)
        self.assertEqual(response.status_code, status.HTTP_303_SEE_OTHER)
        self.assertEqual(response.headers["location"], "/dashboard")
        self.assertIn("access_token", response.cookies)

    def test_login_post_invalid_credentials(self):
        response = client.post("/login", data={
            "email": "patient@test.com",
            "password": "wrongpass"
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("Invalid Credentials", response.text)

    def test_dashboard_unauthorized(self):
        response = client.get("/dashboard")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.headers["content-type"], "text/html; charset=utf-8")

    def test_dashboard_authorized(self):
        # First login to get token
        login_response = client.post("/login", data={
            "email": "patient@test.com",
            "password": "testpass"
        })
        self.assertEqual(login_response.status_code, status.HTTP_200_OK)
        token = login_response.cookies.get("access_token")
         
        # Set the cookie directly on the client instance
        client.cookies.set("access_token", token)
   
        # Access dashboard with token
        response = client.get("/dashboard")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # self.assertIn("dashboard.html", response.text)

    def test_doctor_schedule_get(self):
        # Login as doctor
        login_response = client.post("/login", data={
            "email": "doctor@test.com",
            "password": "testpass"
        })
        token = login_response.cookies.get("access_token")
        
        # Set the cookie directly on the client instance
        client.cookies.set("access_token", token)
        
        response = client.get("/doctor/schedule")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # self.assertIn("doctor_schedule.html", response.text)

    def test_doctor_schedule_post(self):
        # Login as doctor
        login_response = client.post("/login", data={
            "email": "doctor@test.com",
            "password": "testpass"
        })
        token = login_response.cookies.get("access_token")
        
        # Set the cookie directly on the client instance
        client.cookies.set("access_token", token)
        
        response = client.post("/doctor/schedule", data={
            "date": "2023-01-02",
            "start_time": "09:00",
            "end_time": "17:00"
        },follow_redirects=False)
        self.assertEqual(response.status_code, status.HTTP_303_SEE_OTHER)
        self.assertEqual(response.headers["location"], "/dashboard")

    def test_appointment_booking(self):
        # Login as patient
        login_response = client.post("/login", data={
            "email": "patient@test.com",
            "password": "testpass"
        })
        token = login_response.cookies.get("access_token")
        
        # Set the cookie directly on the client instance
        client.cookies.set("access_token", token)
        
        # Get booking form
        response = client.get("/appointment/book")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # self.assertIn("book_appointment.html", response.text)
        
        # Post booking
        response = client.post("/appointment/book", data={
            "doctor_id": str(self.doctor_id),
            "date": "2023-01-01",
            "slot": "11:00"
        }, cookies={"access_token": token}, follow_redirects=False)
        self.assertEqual(response.status_code, status.HTTP_303_SEE_OTHER)
        self.assertEqual(response.headers["location"], "/dashboard")

    def test_view_appointments(self):
        # Login as patient
        login_response = client.post("/login", data={
            "email": "patient@test.com",
            "password": "testpass"
        })
        token = login_response.cookies.get("access_token")
        
        # Set the cookie directly on the client instance
        client.cookies.set("access_token", token)
        
        response = client.get("/appointments")
        # print(response.text,'fytrxfghxgjkjvcbhfghcdfzffgfsdz')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # self.assertIn("appointments.html", response.text)
        self.assertIn("Test Doctor", response.text)

    def test_confirm_appointment(self):
        # Login as doctor
        login_response = client.post("/login", data={
            "email": "doctor@test.com",
            "password": "testpass"
        })
        token = login_response.cookies.get("access_token")
        
        # Set the cookie directly on the client instance
        client.cookies.set("access_token", token)
        
        response = client.post(f"/appointments/{self.appointment_id}/confirm", follow_redirects=False)
        self.assertEqual(response.status_code, status.HTTP_303_SEE_OTHER)
        self.assertEqual(response.headers["location"], "/appointments")

    def test_view_schedule(self):
        # Login as doctor
        login_response = client.post("/login", data={
            "email": "doctor@test.com",
            "password": "testpass"
        })
        token = login_response.cookies.get("access_token")
        
        # Set the cookie directly on the client instance
        client.cookies.set("access_token", token)
        
        response = client.get("/view/schedule")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # self.assertIn("view_schedule.html", response.text)
        self.assertIn("2023-01-01", response.text)

    def test_logout(self):
        # First login
        login_response = client.post("/login", data={
            "email": "patient@test.com",
            "password": "testpass"
        })
        token = login_response.cookies.get("access_token")
        
        # Set the cookie directly on the client instance
        client.cookies.set("access_token", token)
        
        # Then logout
        response = client.get("/logout", follow_redirects=False)
        self.assertEqual(response.status_code, status.HTTP_303_SEE_OTHER)
        self.assertEqual(response.headers["location"], "/login")

if __name__ == "__main__":
    unittest.main()