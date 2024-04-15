import streamlit as st
from streamlit_extras.stylable_container import stylable_container
import PyPDF2
import re
from InvPOCompGemLLM import compare_invoice_po  
from TextExtractGoogleDocAI import extract_text_from_pdf_GoogleDocAI
from ExtractSingleLLM import extract_InvoiceDataLLM, extract_PurchaseOrderDataLLM, extract_Invoice_PO_Compar_DataLLM, extract_Invoice_PO_DetailLLM
import json


def extract_text_from_pdf(file):
    extracted_info = extract_text_from_pdf_GoogleDocAI(file)
    return extracted_info["text"]
    # extracted_info = None
    # return extracted_info

def extract_Invoice_PO_Compar(purchase_order_LLMtext, invoice_LLMtext):
    extracted_info = extract_Invoice_PO_Compar_DataLLM(purchase_order_LLMtext, invoice_LLMtext)
    return extracted_info
    # extracted_info = None
    # return extracted_info

    
def extract_text_from_pdffile(file):
    text = ""
    with file as f:
        pdf_reader = PyPDF2.PdfReader(f)
        for page_num in range(len(pdf_reader.pages)):
            page = pdf_reader.pages[page_num]
            text += page.extract_text()
    return text

def ExtractInvoiceForPayment(llm_response):
    # Extended regular expression pattern to match all desired fields
    pattern = r'"(Invoice\s*no\.|Total|Due\s*Date|Vendor)"\s*:\s*"([^"]*)"'
    
    # Find all matches using the updated pattern
    matches = re.findall(pattern, llm_response)

    # Extract values and return them
    results = {}
    for match in matches:
        results[match[0]] = match[1]

    return results

def ExtractPO_LLM_Fields(llm_response):
    # Define regular expression pattern to match both "Invoice no." and "Total" fields
    pattern = r'"(PO\s*no\.|Total)"\s*:\s*"([^"]*)"'
    
    # Use regular expression to find both "Invoice no." and "Total" fields
    matches = re.findall(pattern, llm_response)
    
    # Extract values and return them
    results = {}
    for match in matches:
        results[match[0]] = match[1]
    
    return results
    
def display_detailed_information(purchase_order_text, invoice_text):
    detailed_result = "Sucess dinesh"#extract_Invoice_PO_DetailLLM(purchase_order_text, invoice_text)
    st.write("# Details", anchor="details")
    st.write(detailed_result)
    
    # Button to go back to comparison
    if st.button("Back to Comparison"):
        st.empty()  # Clear the details page

def gettheFlagFromResponse(json_text,flagName):
    data = json.loads(json_text)

    # Get the value of the 'discrepencyFlag' key
    flag_value = data.get(flagName)

    # Convert the string 'True' to a boolean value if needed
    if flag_value.lower() == 'true':
        flag_value = True
    elif flag_value.lower() == 'false':
        flag_value = False

    return flag_value


