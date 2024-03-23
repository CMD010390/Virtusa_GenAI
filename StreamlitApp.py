import streamlit as st
import PyPDF2
from InvPOCompGemLLM import compare_invoice_po  
from TextExtractGoogleDocAI import extract_text_from_pdf_GoogleDocAI

def extract_text_from_pdf(file):
    extracted_info = extract_text_from_pdf_GoogleDocAI(file)
    return extracted_info["text"]
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

def main():
    st.title("Invoice and Purchase Order Comparison")

    st.sidebar.header("Upload Files")
    purchase_order_file = st.sidebar.file_uploader("Upload Purchase Order PDF", type="pdf")
    invoice_file = st.sidebar.file_uploader("Upload Invoice PDF", type="pdf")

    if purchase_order_file and invoice_file:
        purchase_order_text = extract_text_from_pdf(purchase_order_file)
        invoice_text = extract_text_from_pdf(invoice_file)

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
                result = compare_invoice_po(purchase_order_text, invoice_text)  # Call Gemini LLM processing function
                st.subheader("Comparison Result:")
                st.write(result)  # Display the result

if __name__ == "__main__":
    main()
