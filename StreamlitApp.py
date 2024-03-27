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
    # Define regular expression pattern to match both "Invoice no." and "Total" fields
    pattern = r'"(Invoice\s*no\.|Total)"\s*:\s*"([^"]*)"'
    
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


def main():

    st.sidebar.header("Upload Files")
    purchase_order_file = st.sidebar.file_uploader("Upload Purchase Order PDF", type="pdf")
    invoice_file = st.sidebar.file_uploader("Upload Invoice PDF", type="pdf")
    comparisionFlag = False
    if purchase_order_file and invoice_file:
        purchase_order_text = extract_text_from_pdf(purchase_order_file)
        invoice_text = extract_text_from_pdf(invoice_file)

        invoice_LLMtext = extract_InvoiceDataLLM(invoice_text)
        purchase_order_LLMtext = extract_PurchaseOrderDataLLM(purchase_order_text)
        
        invoiceNo_and_total = ExtractInvoiceForPayment(invoice_LLMtext)
        # Print the results
        Invoice_no= invoiceNo_and_total.get("Invoice no.", "Not found")
        Invoice_Total= invoiceNo_and_total.get("Total", "Not found")
                    
        # st.subheader("Purchase Order Text:")
        # if purchase_order_file:
        #     purchase_order_text = extract_text_from_pdf(purchase_order_file)
        #     st.text_area("Purchase Order Text", purchase_order_text, height=300)

        # st.subheader("Invoice Text:")
        # if invoice_file:
        #     invoice_text = extract_text_from_pdf(invoice_file)
        #     st.text_area("Invoice Text", invoice_text, height=300)

        if st.sidebar.button("Compare"):
            if purchase_order_text and invoice_text:
                st.title("Invoice and Purchase Order Comparison")
                #result = compare_invoice_po(purchase_order_LLMtext, invoice_LLMtext)  # Call Gemini LLM processing function
                result = extract_Invoice_PO_Compar(purchase_order_LLMtext, invoice_LLMtext)
                comparisionFlag = True
                st.subheader("Comparison Result:")
                st.write(result)  # Display the result
                # Show discrepencies pop-up error message

                    
                
        # Buttons for Manual Review and Process Payment
    if(comparisionFlag):
        if st.sidebar.button("Send to Manual Review", help="Send to Manual Review", key="send_to_review"):
        # Functionality for sending to manual review
            pass  # Placeholder for actual functionality
    if(comparisionFlag):    
        if st.sidebar.button(f"Process Payment ({Invoice_Total}) for Invoice ({Invoice_no})", help="Process Payment", key="process_payment"):
        # Functionality for processing payment
            pass  # Placeholder for actual functionality



if __name__ == "__main__":
    main()
