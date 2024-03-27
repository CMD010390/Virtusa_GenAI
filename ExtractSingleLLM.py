
import os
import google.generativeai as genai
from dotenv import load_dotenv

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.prompts import ChatPromptTemplate
from langchain.schema.output_parser import StrOutputParser

load_dotenv()

invoice_text = None
purchase_order_text = None
genai.configure(api_key=os.environ["GOOGLE_API_KEY"])


model = ChatGoogleGenerativeAI(model="gemini-pro",
                               temperature=0.4)

def extract_InvoiceDataLLM(invoice_text):

    prompt = ChatPromptTemplate.from_template(
      
        '''Extract all following values  
      **For each item:**
      : invoice no., Description, 
    Quantity, date, Unit price, Amount, 
    
    and below for entire invoice
    Total, email, phone number and address from this data: {invoice_text} 

     Expected output : remove any dollar symbols {{"Invoice no.":"1001329", 
    "Description":"Office Chair", "Quantity":"2", "Date":"05/01/2022", 
    "Unit price":"1100.00", "Amount":"2200.00"}}{{"Total":"2200.00", "email":"hatwar.dinesh@gmail.com", "phone number":"9999999999",
    "Address":"Mumbai , India"}}
    '''
    )

    output_parser = StrOutputParser()

    chain = prompt | model | output_parser
 
    response = chain.invoke({"invoice_text": invoice_text })
    print("Single LLM Invoice response is ==>>  " + response)

    return response


def extract_PurchaseOrderDataLLM(purchase_order_text):

    prompt = ChatPromptTemplate.from_template(
      
      '''Extract all following values  
      **For each item:**
      : PO no., Description, 
    Quantity, date, Unit price, Amount

    and below for entire PO
    Total, email, phone number and address from this data: {purchase_order_text} 

     Expected output : remove any dollar symbols {{"PO no.":"1001329", 
    "Description":"Office Chair", "Quantity":"2", "Date":"05/01/2022", 
    "Unit price":"1100.00", "Amount":"2200.00"}}{{"Total":"2200.00", "email":"hatwar.dinesh@gmail.com", "phone number":"9999999999",
    "Address":"Mumbai , India"}}
    '''
    )

    output_parser = StrOutputParser()

    chain = prompt | model | output_parser
 
    response = chain.invoke({"purchase_order_text": purchase_order_text })
    print("Single LLM purchase order response is ==>>  " + response)

    return response


def extract_Invoice_PO_Compar_DataLLM(purchase_order_LLMtext, invoice_LLMtext):

    prompt = ChatPromptTemplate.from_template(
      
        '''Here's an text invoice:\n {invoice_LLMtext} \n and a purchase order:\n {purchase_order_LLMtext} \n Are there any discrepancies in quantity of item, number of items or total between the invoice and purchase order?'''
    )

    output_parser = StrOutputParser()

    chain = prompt | model | output_parser
 
    response = chain.invoke({"invoice_LLMtext": invoice_LLMtext, "purchase_order_LLMtext": purchase_order_LLMtext })
    print("Single LLM Comparision response is ==>>  " + response)

    return response


def extract_Invoice_PO_DetailLLM(purchase_order_LLMtext, invoice_LLMtext):

    prompt = ChatPromptTemplate.from_template(
      
        '''Here's an text invoice:\n {invoice_LLMtext} \n and a purchase order:\n {purchase_order_LLMtext} \n Find the detailed discrepancies between Invoice and purchase order '''
    )

    output_parser = StrOutputParser()

    chain = prompt | model | output_parser
 
    response = chain.invoke({"invoice_LLMtext": invoice_LLMtext, "purchase_order_LLMtext": purchase_order_LLMtext })
    print("Single LLM detailed response is ==>>  " + response)

    return response
