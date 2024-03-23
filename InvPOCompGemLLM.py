
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
                               temperature=0.0)

# Hardcoded text
# invoice_text = """
# Invoice Number: INV-00123
# Vendor: TCS Inc.
# Items:
#   - Item: Widget
#     Quantity: 50
#     Price: $10.50 per unit
#   - Item: Pencil
#     Quantity: 50
#     Price: $1.00 per unit

# Subtotal: $550.00
# Tax (8%): $44.00
# Total: $594.00
# """

# purchase_order_text = """
# Purchase Order Number: PO-45678
# Vendor: TCS Inc. 
# Items:
#   - Item: Widget
#     Quantity: 50
#     Price: $10.80 per unit 
#   - Item: Pencil
#     Quantity: 50
#     Price: $1.00 per unit
# """ 



def compare_invoice_po(purchase_order_text, invoice_text):
 print(">>>>>>>>>>>>>>>Invoice Text<<<<<<<<<<<<<<<<<")
 print(invoice_text)
 print(">>>>>>>>>>>>>>>purchase_order_text <<<<<<<<<<<<<<<<<")
 print(purchase_order_text)

 prompt = ChatPromptTemplate.from_template(

 #"""Here's an text invoice:\n {invoice_text} \n and a purchase order:\n {purchase_order_text} \n Are there any discrepancies in quantity or price between the invoice and purchase order?"""
  """
  Here is an invoice for the same purchase order:

{invoice_text}

Here is a purchase order:

{purchase_order_text}


Please compare the information in the purchase order and invoice, focusing on the following:

* **General Details:**
    * Any mismatches in details with similar meanings (e.g., "Purchase Order Number" vs. "Order ID")
* **Items:**
    * Discrepancies in quantities of any item
    * **Identify missing items:**
        * Check for items listed in the invoice that are not present in the purchase order.
    * **Ignore additional details in the invoice description:**
        * If the purchase order lists an item (e.g., "paper"), the invoice can mention it with additional details (e.g., "5 reams of A4 paper"). Don't consider this a discrepancy.
* **Amounts:**
    * **Consider both scenarios:**
        * If the purchase order only has a total amount:
            * Compare the total amount in the purchase order with the final total amount (including tax) in the invoice.
        * If the purchase order has a subtotal and the invoice has a subtotal and tax:
            * Compare the subtotal amount in the purchase order with the subtotal amount in the invoice.
    * Variations in tax amounts (if applicable in the invoice and purchase order). Ignore tax descripencies if purchase order doesnt have the tax details.

**Example Output:**

There is a discrepancy in the quantity of pens. The purchase order lists "10 boxes of pens", while the invoice lists "12 pens". If there is any extra item in any of the invoice or purchase order. 

"""
 )

 output_parser = StrOutputParser()

 chain = prompt | model | output_parser
 
 response = chain.invoke({"purchase_order_text": purchase_order_text,"invoice_text": invoice_text })
 print("LLM response is ==>>  " + response)

  # Analyze response for discrepancies
#  discrepancies = {}
#  if "discrepancy" in response.lower():
#     # Check for quantity discrepancy
#     if "quantity" in response.lower():
#       discrepancies["quantity"] = True
#     # Check for price discrepancy
#     if "price" in response.lower():
#       discrepancies["price"] = True
#  else:
#     # No discrepancies found
#     return "Nothing found"

 return response


# Compare invoice and PO
# discrepancies = compare_invoice_po(purchase_order_text, invoice_text)

# # Check for and print discrepancies
# if discrepancies:
#   print("##################### >> Here is the final result << ######################")
#   print("Identified discrepancies:")
#   for key, value in discrepancies.items():
#     print(f"- {key.capitalize()}")
# else:
#   print("No discrepancies found between invoice and purchase order based on Gemini's analysis.")
