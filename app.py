from fastapi import FastAPI, File, UploadFile
from fastapi.responses import FileResponse
import os
from src.utils import main_api, email, pasw, get_browser
from src.login_script import login

app = FastAPI()

screenshots = "screenshots"
driver = login(quit=False, headless=False)
print("log in done")
def generate_pdf(input_text):
    # Check if the directory exists
    if os.path.exists(screenshots):
        # Directory exists, remove files within it
        for filename in os.listdir(screenshots):
            file_path = os.path.join(screenshots, filename)
            os.remove(file_path)  # Remove individual files
    else:
        # Directory doesn't exist, create it
        os.makedirs(screenshots)
    
    
    main_api(url='https://www.carfaxonline.com/', email=email, pasw=pasw, vin=input_text,  driver=driver)
    pdf_path = os.path.join(os.getcwd(),"PDF_API",f"{input_text}.pdf")
    return pdf_path



@app.post("/generate-pdf/")
async def response_pdf(input_text: str):
    # generate pdf and return the path
    pdf_path = generate_pdf(input_text)
    # PDF file path
    # pdf_path = os.path.join(os.getcwd(),"pdf",f"{input_text}.pdf")
    # #pdf_path = r"F:\Creative AI\carfax_oct_4 (1)\carfax\PDF\3FA6P0LU7KR210642.pdf"

    # Return the PDF file
    return FileResponse(pdf_path, media_type='application/pdf', filename=f"{input_text}.pdf")



