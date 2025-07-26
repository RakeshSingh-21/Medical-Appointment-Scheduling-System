from sqlalchemy import Column, Integer, String, ForeignKey, Time, Date,Boolean
from sqlalchemy.orm import relationship
from database import Base

#User Model
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), index=True)
    email = Column(String(20), unique=True, index=True)
    password_hash = Column(String(225))
    role = Column(String(50), nullable=False)
    
    appointments = relationship("Appointment", back_populates="patient", foreign_keys="[Appointment.patient_id]")
    doctor_schedule = relationship("DoctorSchedule", back_populates="doctor", foreign_keys="[DoctorSchedule.doctor_id]")
    doctor_appointments = relationship("Appointment", back_populates="doctor", foreign_keys="[Appointment.doctor_id]")


#Doctor Schedule Table
class DoctorSchedule(Base):
    __tablename__ = "doctor_schedule"
    
    id = Column(Integer, primary_key=True, index=True)
    doctor_id = Column(Integer, ForeignKey("users.id"))
    date = Column(Date, nullable=False)
    start_time = Column(Time, nullable=False)
    end_time = Column(Time, nullable=False)
    
    doctor = relationship("User", back_populates= "doctor_schedule")
    
    
#Appointments Table
class Appointment(Base):
    __tablename__ = "appointments"
    
    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("users.id"))
    doctor_id = Column(Integer, ForeignKey("users.id"))
    date = Column(Date, nullable=False)
    time = Column(Date, nullable=True) 
    status = Column(String(50), nullable=False) #e.g., "pending", "confirmed", "cancelled"
    
    patient = relationship("User", back_populates="appointments", foreign_keys=[patient_id])
    doctor = relationship("User", back_populates="doctor_appointments", foreign_keys=[doctor_id])