from fastapi import FastAPI, File, UploadFile
from fastapi.responses import FileResponse
import os
from src.utils import main_api, email, pasw, get_browser
from src.login_script import login
from fastapi.responses import JSONResponse

app = FastAPI()

driver_second = login(quit=False, headless=False)
print("log in done")

def remove_pdf(path = "PDF_API"):
    for file in os.listdir(path):
        os.remove(os.path.join(path, file))
        print("Pdf has deleted from PDF API")

def screenshots_func(screenshots):
    if os.path.exists(screenshots):
        # Directory exists, remove files within it
        for filename in os.listdir(screenshots):
            file_path = os.path.join(screenshots, filename)
            os.remove(file_path)  # Remove individual files
    else:
        # Directory doesn't exist, create it
        os.makedirs(screenshots)


def generate_pdf_second(input_text, driver = driver_second):
    # Check if the directory exists
    remove_pdf()
    screenshots = "screenshots_api_2"
    screenshots_func(screenshots = screenshots)
    
    is_vin_correct = main_api(url='https://www.carfaxonline.com/', email=email, pasw=pasw, vin=input_text,  driver=driver, screenshot_name = screenshots)
    pdf_path = os.path.join(os.getcwd(),"PDF_API",f"{input_text}.pdf")
    return pdf_path, is_vin_correct
    


@app.post("/generate-pdf_one/")
def response_pdf_one(input_text: str):
    # generate pdf and return the path
    pdf_path, is_vin_correct = generate_pdf_second(input_text)

    # Return the PDF file
    if is_vin_correct:
        return  FileResponse(pdf_path, media_type='application/pdf', filename=f"{input_text}.pdf", status_code=200)
    else:
        return JSONResponse(content={"error": "VIN not found", "is_vin_correct": is_vin_correct}, status_code=400)


