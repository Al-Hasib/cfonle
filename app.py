from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, JSONResponse
import os
from src.utils import main_api_with_retry, email, pasw
from src.login_script import login

app = FastAPI()

def remove_pdf(path="PDF_API"):
    if os.path.exists(path):
        for file in os.listdir(path):
            os.remove(os.path.join(path, file))
            print("PDF deleted from PDF_API")

def screenshots_func(screenshots):
    if os.path.exists(screenshots):
        for filename in os.listdir(screenshots):
            file_path = os.path.join(screenshots, filename)
            os.remove(file_path)
    else:
        os.makedirs(screenshots)

def generate_pdf(input_text, screenshots="screenshots_api"):
    remove_pdf()
    screenshots_func(screenshots=screenshots)
    
    # Use enhanced main_api_with_retry instead of main_api
    is_vin_correct = main_api_with_retry(
        url='https://www.carfaxonline.com/', 
        email=email, 
        pasw=pasw, 
        vin=input_text, 
        screenshot_name=screenshots
    )
    
    pdf_path = os.path.join(os.getcwd(), "PDF_API", f"{input_text}.pdf")
    return pdf_path, is_vin_correct

@app.post("/generate-pdf/")
def response_pdf(input_text: str):
    try:
        pdf_path, is_vin_correct = generate_pdf(input_text)
        
        if is_vin_correct and os.path.exists(pdf_path):
            return FileResponse(pdf_path, media_type='application/pdf', filename=f"{input_text}.pdf")
        else:
            raise HTTPException(status_code=400, detail="VIN not found or PDF generation failed")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.post("/generate-pdf_one/")
def response_pdf_one(input_text: str):
    try:
        pdf_path, is_vin_correct = generate_pdf(input_text, "screenshots_api_1")
        
        if is_vin_correct and os.path.exists(pdf_path):
            return FileResponse(pdf_path, media_type='application/pdf', filename=f"{input_text}.pdf")
        else:
            return JSONResponse(
                content={"error": "VIN not found", "is_vin_correct": is_vin_correct}, 
                status_code=400
            )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
