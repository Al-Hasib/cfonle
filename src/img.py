import img2pdf, os 
from PIL import Image
import re

def alphanumeric_sort(items):
    return sorted(items, key=lambda x: [int(i) if i.isdigit() else i for i in re.split('(\d+)', x)])

# Function to read images from a directory and stack them vertically
def stack_images_vertically(image_dir):
    # List to store image objects
    images = []
    
    # Loop through all files in the directory
    for filename in alphanumeric_sort(os.listdir(image_dir)):
        if filename.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp')):  # Supported image formats
            img_path = os.path.join(image_dir, filename)
            img = Image.open(img_path)

            # Convert images to 'RGB' if they are in a different mode
            if img.mode != 'RGB':
                img = img.convert('RGB')
            
            images.append(img)

    # Stack images vertically
    if images:
        # Calculate total height and max width for the new image
        total_height = sum(img.height for img in images)
        max_width = max(img.width for img in images)

        # Create a new blank image with the appropriate dimensions
        stacked_image = Image.new('RGB', (max_width, total_height))

        # Paste each image into the stacked image
        current_y = 0
        for img in images:
            stacked_image.paste(img, (0, current_y))
            current_y += img.height

        return stacked_image
    return None

# def convert_folder_to_pdf(folder_path, output_path):
#     image_paths = []
#     for filename in alphanumeric_sort(os.listdir(folder_path)):
#         if filename.lower().endswith(('.png', '.jpg', '.jpeg', '.gif')):
#             image_path = os.path.join(folder_path, filename)
#             image_paths.append(image_path)

#     with open(output_path, "wb") as f:
#         print(image_paths)
#         f.write(img2pdf.convert(image_paths,
#                                 cropborder=None,  # No crop border
#                                 bleedborder=None,  # No bleed border
#                                 trimborder=None,  # No trim border
#                                 artborder=None))

def convert_folder_to_pdf(folder_path, output_path):
    # Create a stacked image
    stacked_image = stack_images_vertically(folder_path)

    if stacked_image:
        # Save the stacked image as a temporary file
        stacked_image_path = 'screenshots/temp_stacked_image.jpg'
        stacked_image.save(stacked_image_path)
        print("stacked image saved")

        # Convert the stacked image to PDF
        with open(output_path, 'wb') as f:
            f.write(img2pdf.convert(stacked_image_path))

        print("PDF created successfully: output.pdf")
    else:
        print("No images found in the specified directory.")



if __name__ == '__main__':
    # Example usage
    folder_path = 'SS'
    output_path = 'output.pdf'
    convert_folder_to_pdf(folder_path, output_path)