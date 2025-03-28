from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy import Column, Integer, Float, String
from sqlalchemy.orm import Session
from database import Base, engine, get_db
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
import os
import requests
import pika  # ✅ Import RabbitMQ client
import json
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM")



#EVENT_SERVICE_URL = "http://event-service:4000/events/"

# Check if running inside Kubernetes
if os.getenv("KUBERNETES_SERVICE_HOST"):
    EVENT_SERVICE_URL = os.getenv("EVENT_SERVICE_URL", "http://event-service.onlineeventbookingamaar.svc.cluster.local:4000/events/")
    print(f"DEBUG: EVENT_SERVICE_URL = {EVENT_SERVICE_URL}")

else:
    EVENT_SERVICE_URL = "http://event-service:4000/events/"  # Default for Docker Compose
    print(f"DEBUG: EVENT_SERVICE_URL = {EVENT_SERVICE_URL}")


# RabbitMQ settings
RABBITMQ_HOST = "rabbitmq"  # Use the service name from Docker Compose

QUEUE_NAME = "booking_queue"

# Initialize FastAPI
app = FastAPI()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="users/login")

# ✅ Create Database Tables
Base.metadata.create_all(bind=engine)




@app.get("/")
def read_root():
    return {"message": "Booking Service is Running!"}


# ✅ Booking Model (Table)
class Booking(Base):
    __tablename__ = "bookings"
    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(String, nullable=False)
    amount = Column(Float, nullable=False)
    num_tickets = Column(Integer, nullable=False)
    user_id = Column(Integer, nullable=False)  # No ForeignKey constraint

# ✅ Pydantic Schema for Request Body
class BookingCreate(BaseModel):
    event_id: str
    amount: float
    num_tickets: int

def verify_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: int = payload.get("id")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid token")
        return user_id
    except JWTError as e:
        raise HTTPException(status_code=401, detail="Invalid token")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error decoding token: {e}")

# ✅ Function to Check if Event Exists
def check_event_exists(event_id: str):
    try:
        response = requests.get(f"{EVENT_SERVICE_URL}{event_id}")
        if response.status_code != 200:
            raise HTTPException(status_code=404, detail="Event not found or unavailable")
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"❌ Error contacting event service: {e}")
        raise HTTPException(status_code=500, detail=f"Error contacting event service: {e}")

# ✅ Function to Publish Message to RabbitMQ
def publish_booking_message(user_id: int, amount: str, num_tickets: str):
    try:
        # Establish connection
        connection = pika.BlockingConnection(pika.ConnectionParameters(RABBITMQ_HOST))
        channel = connection.channel()

        # Declare queue
        channel.queue_declare(queue=QUEUE_NAME, durable=True)

        # Create message payload
        message = json.dumps({
            "user_id": user_id,
            "amount": amount,
            "num_tickets": num_tickets
        })

        # Publish message
        channel.basic_publish(
            exchange="",
            routing_key=QUEUE_NAME,
            body=message
        )

        # Close connection
        connection.close()
        print(f"📤 Sent booking message: {message}")
    except Exception as e:
        print(f"❌ Error publishing to RabbitMQ: {e}")
        raise HTTPException(status_code=500, detail=f"Error publishing to RabbitMQ: {e}")

@app.post("/bookings")
def create_booking(
    booking: BookingCreate,
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
):
    try:
        user_id = verify_token(token)  # ✅ Get user ID from token
        event_data = check_event_exists(booking.event_id)  # ✅ Check if event exists before booking
        
        # Create new booking object
        new_booking = Booking(
            event_id=booking.event_id,
            amount=booking.amount,
            num_tickets=booking.num_tickets,
            user_id=user_id
        )

        # Add booking to database and commit
        db.add(new_booking)
        db.commit()
        db.refresh(new_booking)

        # Send message to RabbitMQ
        publish_booking_message(user_id, booking.amount, booking.num_tickets)

        return {"message": "Booking successful", "booking_id": new_booking.id, "event": event_data}
    
    except Exception as e:
        print(f"❌ Error creating booking: {e}")
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {e}")

# ✅ GET Endpoint to Fetch User's Bookings
@app.get("/bookings")
def get_user_bookings(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
):
    user_id = verify_token(token)
    bookings = db.query(Booking).filter(Booking.user_id == user_id).all()
    return {"user_id": user_id, "bookings": bookings}