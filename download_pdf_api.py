
import os
import requests

# API Endpoint
api_url = "http://54.225.0.46:8000/generate-pdf_one/"

# VIN Number (Modify as needed)
vin_number = "3FA6P0LU7KR210642"


def get_pdf(api_url="http://54.225.0.46:8000/generate-pdf_one/", vin_number="3FA6P0LU7KR210642", pdf_folder="PDF"):
    # Send API Request
    response = requests.post(api_url, params={"input_text": vin_number}, stream=True)

    # Check Response Status
    if response.status_code == 200:
        pdf_filename = f"{vin_number}.pdf"
        pdf_path = os.path.join(pdf_folder, pdf_filename)
        
        # Save the PDF file
        with open(pdf_path, "wb") as pdf_file:
            for chunk in response.iter_content(chunk_size=1024):
                pdf_file.write(chunk)
        
        print(f"PDF downloaded successfully: {pdf_filename}")
        return True
    else:
        print(f"Failed to download PDF. Status Code: {response.status_code}")
        # print("Response:", response.text)
        return False

