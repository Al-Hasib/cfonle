from fastapi import FastAPI, File, UploadFile
from fastapi.responses import FileResponse
import os
from src.utils import main_api, email, pasw, get_browser
from src.login_script import login
from fastapi.responses import JSONResponse
import pandas as pd
import aiocron


app = FastAPI()


driver_first = login(quit=False, headless=False)
driver_second = login(quit=False, headless=False)
print("log in done")

DATA_PATH = "data.csv"

def update_limit_column():
    df = pd.read_csv(DATA_PATH)

    df['used'] = 0  # you can set logic here to compute values
    
    # Save updated data
    df.to_csv(DATA_PATH, index=False)
    print("Limit column updated")

# Schedule this to run every day at midnight (00:00)
@aiocron.crontab('0 0 * * *')  # runs daily at 00:00
async def scheduled_task():
    update_limit_column()

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

def generate_pdf(input_text, driver = driver_first):
    # Check if the directory exists
    remove_pdf()
    screenshots = "screenshots_api"
    screenshots_func(screenshots = screenshots)

    pdf_path = os.path.join(os.getcwd(),"PDF_API",f"{input_text}.pdf")
    is_vin_correct = main_api(url='https://www.carfaxonline.com/', email=email, pasw=pasw, vin=input_text,  driver=driver, screenshot_name = screenshots)
    pdf_path = os.path.join(os.getcwd(),"PDF_API",f"{input_text}.pdf")
    return pdf_path

def generate_pdf_second(input_text, driver = driver_second):
    # Check if the directory exists
    remove_pdf()
    screenshots = "screenshots_api_1"
    screenshots_func(screenshots = screenshots)
    
    is_vin_correct = main_api(url='https://www.carfaxonline.com/', email=email, pasw=pasw, vin=input_text,  driver=driver, screenshot_name = screenshots)
    pdf_path = os.path.join(os.getcwd(),"PDF_API",f"{input_text}.pdf")
    return pdf_path, is_vin_correct
    
    



@app.post("/generate-pdf/")
def response_pdf(input_text: str):
    # generate pdf and return the path
    pdf_path = generate_pdf(input_text)

    return FileResponse(pdf_path, media_type='application/pdf', filename=f"{input_text}.pdf")


@app.post("/generate-pdf_one/")
def response_pdf_one(input_text: str):
    # generate pdf and return the path
    pdf_path, is_vin_correct = generate_pdf_second(input_text)

    # Return the PDF file
    if is_vin_correct:
        return  FileResponse(pdf_path, media_type='application/pdf', filename=f"{input_text}.pdf", status_code=200)
    else:
        return JSONResponse(content={"error": "VIN not found", "is_vin_correct": is_vin_correct}, status_code=400)


@app.post("/accept_Id")
def accept_Id(Id: int):
    df = pd.read_csv("data.csv")
    df.loc[df['Id'] == Id, 'status'] = 'active'
    df.to_csv('data.csv', index=False)

    filter_data = df[df['Id'] == Id]

    if filter_data.empty:
        return {"error": "Id not found"}

    # Convert to native Python types
    name = str(filter_data['name'].values[0])
    id_val = int(filter_data['Id'].values[0])
    status = str(filter_data['status'].values[0])

    return {
        "name": name,
        "Id": id_val,
        "Status": status
    }


@app.post("/reject_Id")
def reject_Id(Id:int):
    df = pd.read_csv("data.csv")
    df.loc[df['Id'] == Id, 'status'] = 'reject'
    df.to_csv('data.csv', index=False)
    filter_data = df[df['Id']==Id]
    if filter_data.empty:
        return {"error": "Id not found"}
    name = str(filter_data['name'].values[0])
    id = int(filter_data['Id'].values[0])
    status = str(filter_data['status'].values[0])

    return {
        "name":name,
        "Id":id,
        "Status":status
    }

@app.get("/show_pending")
def show_pending():
    df = pd.read_csv("data.csv")
    active_data = df[df['status'] == 'pending']
    data_dict = active_data.to_dict(orient='records')
    return{
        "Pending_data": data_dict
    }

@app.get_all("/all_data")
def get_all():
    df = pd.read_csv("data.csv")

    return {"data":df}



