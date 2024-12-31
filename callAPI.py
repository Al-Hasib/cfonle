import requests


def get_pdf(url="http://54.225.0.46:8000/generate-pdf/", vin="3FTTW8E3XNRA75034"):

    # Query parameters
    params = {
        "input_text": vin,
    }

    # A POST request to the API with query parameters
    response = requests.post(url, params=params)

    # Print the response
    if response.status_code == 200:
        print("PDF generated and retrieved successfully!")
        # Save the PDF file
        with open(f"{vin}.pdf", "wb") as file:
            file.write(response.content)
    else:
        print(f"Failed to generate PDF. Status code: {response.status_code}")
        print(response.text)


if __name__=="__main__":
    vin = "3FTTW8E3XNRA75034"
    get_pdf(vin=vin)