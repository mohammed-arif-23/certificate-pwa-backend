import os
import pandas as pd
from fastapi import FastAPI, HTTPException, BackgroundTasks, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.utils import ImageReader
from reportlab.lib.colors import HexColor
import aiosmtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from dotenv import load_dotenv
import logging
import httpx

# Load environment variables
load_dotenv()

# Setup Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

# CORS
origins = ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global Data
EMAIL_TO_NAME = {}
CSV_PATH = os.path.join(os.path.dirname(__file__), "data", "data.csv")
TEMPLATE_PATH = os.path.join(os.path.dirname(__file__), "templates", "certificate_template.png")
GENERATED_DIR = os.path.join(os.path.dirname(__file__), "generated")
os.makedirs(GENERATED_DIR, exist_ok=True)

# Supabase Config
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

@app.on_event("startup")
async def startup_event():
    global EMAIL_TO_NAME
    try:
        if os.path.exists(CSV_PATH):
            df = pd.read_csv(CSV_PATH)
            # Normalize column names
            df.columns = [c.strip() for c in df.columns]
            
            # Smart column finding
            email_col = next((c for c in df.columns if "email" in c.lower()), None)
            name_col = next((c for c in df.columns if "name" in c.lower()), None)

            if email_col and name_col:
                for _, row in df.iterrows():
                    val = row[email_col]
                    if pd.isna(val): continue
                    # Robust cleaning: strip and remove internal spaces
                    email = str(val).strip().lower().replace(" ", "")
                    name = str(row[name_col]).strip()
                    EMAIL_TO_NAME[email] = name
                logger.info(f"Loaded {len(EMAIL_TO_NAME)} records.")
            else:
                logger.error("Could not find Email/Name columns.")
        else:
            logger.warning("CSV file not found.")
    except Exception as e:
        logger.error(f"Error loading CSV: {e}")

# Models
class EmailRequest(BaseModel):
    email: str

class FeedbackRequest(BaseModel):
    email: str
    rating: int
    q1: str  # Relevance
    q2: str  # Confidence
    q3: str  # Instructors
    q4: str  # Duration
    q5: str  # Satisfaction

# Helper: Generate PDF
def create_certificate(name: str) -> str:
    filename = f"certificate_{name.replace(' ', '_')}.pdf"
    output_path = os.path.join(GENERATED_DIR, filename)
    
    # Determine page size from image
    if os.path.exists(TEMPLATE_PATH):
        try:
            image = ImageReader(TEMPLATE_PATH)
            img_width, img_height = image.getSize()
            width, height = img_width, img_height
        except Exception as e:
            logger.error(f"Error reading template size: {e}")
            width, height = landscape(A4) # Fallback
    else:
        width, height = landscape(A4)

    c = canvas.Canvas(output_path, pagesize=(width, height))
    
    # Draw background
    if os.path.exists(TEMPLATE_PATH):
        try:
            c.drawImage(TEMPLATE_PATH, 0, 0, width=width, height=height) 
        except Exception as e:
            logger.error(f"Error loading template: {e}")
            
    # Register Custom Font
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    
    font_path = os.path.join(os.path.dirname(__file__), "fonts", "Poppins-Bold.ttf")
    if os.path.exists(font_path):
        try:
            pdfmetrics.registerFont(TTFont('Poppins-Bold', font_path))
            font_name = 'Poppins-Bold'
        except Exception as e:
            logger.error(f"Error registering font: {e}")
            font_name = 'Helvetica-Bold'
    else:
        logger.warning(f"Font file not found at {font_path}")
        font_name = 'Helvetica-Bold'

    # Name Configuration
    c.setFont(font_name, 25)
    c.setFillColor(HexColor("#000")) # Black
    
    text_width = c.stringWidth(name, font_name, 25)
    # Center horizontally, adjusted with user's specific offset
    x = ((width - text_width) / 2) + 50
    
    # Vertical position
    y = 235 
    
    c.drawString(x, y, name)
    c.save()
    return output_path

async def send_email_async(recipient: str, pdf_path: str):
    if not os.getenv("SMTP_USER") or not os.getenv("SMTP_PASSWORD"):
        logger.warning("No SMTP credentials")
        return
    msg = MIMEMultipart()
    msg["From"] = os.getenv("SMTP_USER")
    msg["To"] = recipient
    msg["Subject"] = "Your Certificate - Valli Hospital"
    body = MIMEText("Thank you for your feedback! Here is your certificate.")
    msg.attach(body)
    with open(pdf_path, "rb") as f:
        att = MIMEApplication(f.read(), _subtype="pdf")
        att.add_header("Content-Disposition", "attachment", filename=os.path.basename(pdf_path))
        msg.attach(att)
    try:
        await aiosmtplib.send(
            msg,
            hostname=os.getenv("SMTP_HOST"),
            port=587,
            username=os.getenv("SMTP_USER"),
            password=os.getenv("SMTP_PASSWORD"),
            start_tls=True,
        )
    except Exception as e:
        logger.error(f"Email error: {e}")

@app.post("/verify-email")
async def verify_email(data: EmailRequest):
    # Robust cleaning: strip and remove internal spaces
    email = data.email.strip().lower().replace(" ", "")
    if email in EMAIL_TO_NAME:
        # Check if already submitted
        has_submitted = False
        if SUPABASE_URL and SUPABASE_KEY:
            try:
                async with httpx.AsyncClient() as client:
                    resp = await client.get(
                        f"{SUPABASE_URL}/rest/v1/feedback",
                        params={"email": f"eq.{email}", "select": "email"},
                        headers={
                            "apikey": SUPABASE_KEY,
                            "Authorization": f"Bearer {SUPABASE_KEY}",
                        }
                    )
                    if resp.status_code == 200 and len(resp.json()) > 0:
                        has_submitted = True
            except Exception as e:
                logger.error(f"Supabase check failed: {e}")

        return {"valid": True, "name": EMAIL_TO_NAME[email], "has_submitted": has_submitted}
    raise HTTPException(status_code=404, detail="Email not found")

@app.post("/feedback")
async def submit_feedback(data: FeedbackRequest):
    if not SUPABASE_URL or not SUPABASE_KEY:
        raise HTTPException(status_code=500, detail="Database not configured")
    
    url = f"{SUPABASE_URL}/rest/v1/feedback"
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=minimal"
    }
    payload = {
        "email": data.email,
        "rating": data.rating,
        "q1_relevance": data.q1,
        "q2_confidence": data.q2,
        "q3_instructor": data.q3,
        "q4_duration": data.q4,
        "q5_satisfaction": data.q5
    }
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(url, json=payload, headers=headers)
            if response.status_code >= 400:
                logger.error(f"Supabase error: {response.text}")
                raise HTTPException(status_code=500, detail=response.text)
            return {"status": "success"}
        except Exception as e:
            logger.error(f"Request error: {e}")
            raise HTTPException(status_code=500, detail=str(e))

@app.post("/generate-certificate")
async def generate_certificate_endpoint(data: EmailRequest):
    try:
        email = data.email.strip().lower().replace(" ", "")
        name = EMAIL_TO_NAME.get(email)
        if not name: raise HTTPException(status_code=404, detail="Name not found")
        pdf = create_certificate(name)
        return FileResponse(pdf, media_type='application/pdf', filename=os.path.basename(pdf))
    except Exception as e:
        logger.error(f"Certificate generation failed: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/send-certificate")
async def send_certificate_endpoint(data: EmailRequest, bg_tasks: BackgroundTasks):
    email = data.email.strip().lower().replace(" ", "")
    name = EMAIL_TO_NAME.get(email)
    if not name: raise HTTPException(status_code=404)
    pdf = create_certificate(name)
    bg_tasks.add_task(send_email_async, email, pdf)
    return {"status": "sending"}

# --- Admin Panel Endpoints ---

class AdminLoginRequest(BaseModel):
    username: str
    password: str

@app.post("/admin/login")
async def admin_login(data: AdminLoginRequest):
    # Hardcoded credentials for simplicity
    if data.username == "admin" and data.password == "admin123":
        return {"status": "success", "token": "fake-jwt-token"}
    raise HTTPException(status_code=401, detail="Invalid credentials")

@app.get("/admin/feedback")
async def get_all_feedback():
    if not SUPABASE_URL or not SUPABASE_KEY:
        raise HTTPException(status_code=500, detail="DB not configured")
    
    url = f"{SUPABASE_URL}/rest/v1/feedback?select=*" # Get all columns
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
    }
    
    async with httpx.AsyncClient() as client:
        resp = await client.get(url, headers=headers)
        if resp.status_code != 200:
            raise HTTPException(status_code=500, detail=resp.text)
        
        data = resp.json()
        # Enrich with names
        for item in data:
            email_key = item.get('email', '').strip().lower().replace(" ", "")
            item['name'] = EMAIL_TO_NAME.get(email_key, item.get('email')) # Fallback to email if name not found
            
        return data

@app.get("/admin/stats")
async def get_admin_stats():
    # Reuse get_all_feedback logic or call Supabase directly
    # For now, fetch all and compute stats in Python (easiest for small datasets)
    data = await get_all_feedback()
    df = pd.DataFrame(data)
    
    stats = {
        "total_feedback": len(data),
        "average_rating": 0,
        "rating_counts": {1:0, 2:0, 3:0, 4:0, 5:0}
    }
    
    if not df.empty and "rating" in df.columns:
        stats["average_rating"] = round(df["rating"].mean(), 2)
        counts = df["rating"].value_counts().to_dict()
        for k, v in counts.items():
            stats["rating_counts"][int(k)] = int(v)
            
    return stats

@app.delete("/admin/feedback/{email}")
async def delete_feedback(email: str):
    if not SUPABASE_URL or not SUPABASE_KEY:
        raise HTTPException(status_code=500, detail="DB not configured")

    url = f"{SUPABASE_URL}/rest/v1/feedback?email=eq.{email}"
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
    }
    
    async with httpx.AsyncClient() as client:
        resp = await client.delete(url, headers=headers)
        if resp.status_code >= 400:
             raise HTTPException(status_code=500, detail=resp.text)
        return {"status": "deleted"}
