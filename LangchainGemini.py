from dotenv import load_dotenv
load_dotenv()
import streamlit as st
import os
from PIL import Image
import google.generativeai as genai
GOOGLE_API_KEY= "MyGeminiKey"

genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
model=genai.GenerativeModel("gemini-pro-vision")
def get_gemini_response(input,image,prompt):
    response: model.generate_content([input,image[0],prompt])
    return response.text
def input_image_details(uploaded_file):
    if uploaded_file is not None:
        bytes_data = uploaded_file.getvalue()

        image_parts = [
            {
                "mime_type": uploaded_file.type,
                "data": bytes_data
            }
        ]
        return image_parts
    else:
        raise FileExistsError("No file uploaded")


st.set_page_config(page_title="Invoice Extractor")
st.header("Invoice Extractor")
input=st.text_input("input Prompt: ", key="input")
uploaded_file = st.file_uploader("choose an image of the Invoice",type=["jpg","jpeg","png"])
image=""
if uploaded_file is not None:
    image=Image.open (uploaded_file)
    st.image(image, caption="uploaded Image", use_column_width=True)

submit=st.button("Ask me about invoice")

input_prompt="""
You are an expert in understanding invoice. we will upoad an image as a invoice an you will have to answer anuy questions based on uploaded invoice image
"""

if submit:
    image_data=input_image_details(uploaded_file)
    response=get_gemini_response(input_prompt,image_data,input)
    st.subheader("The response is")
    st.write(response)
