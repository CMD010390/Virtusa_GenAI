from google.cloud import documentai_v1beta3 as documentai
from google.oauth2.service_account import Credentials
import os
from dotenv import load_dotenv

load_dotenv()
project_id=os.environ["PROJECT_ID"]
location=os.environ["LOCATION"]
processor_id=os.environ["PROCESSOR_ID"]

credentials = Credentials.from_service_account_file("//Users/dineshhatwar/Desktop/Dinesh/Keys/Manoj/my-project-doc-ai-417311-45aae75f489d.json")

def extract_text_from_pdf_GoogleDocAI(pdf_file):
    # Initialize the Document AI client
    client = documentai.DocumentProcessorServiceClient(credentials=credentials)

    # Construct the processor resource name
    processor_name = f"projects/{project_id}/locations/{location}/processors/{processor_id}"
    
    # Read the PDF file
    # with open(file_path, "rb") as pdf_file:
    #      content = pdf_file.read()

    # Create a document object  
    document = {"content": pdf_file.read(), "mime_type": "application/pdf"}
    # Process the document
    request = {"name": processor_name, "document": document}
    result = client.process_document(request)
    # Extract information from the result
    document_text = result.document.text
    document_pages = result.document.pages

    return {"text": document_text, "pages": document_pages}

