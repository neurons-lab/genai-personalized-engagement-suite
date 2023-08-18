#!/usr/bin/env python
"""AWS Bedrock and AI21 Lab with Jurassic-2 Ultra model
Personalized Email Promo
Version: 0.1.0
"""
import boto3
import json

import pandas as pd
import streamlit as st

bedrock = boto3.client(
    service_name='bedrock',
    region_name='us-west-2',
    endpoint_url='https://bedrock.us-west-2.amazonaws.com',
)

def j2_invoke(prompt_data, max_tokens=250,temperature=0.9,top_p=1, model_id='ai21.j2-ultra'):
    """Invoke J2 model
    
    Parameters:
    prompt_data (str): Prompt data
    max_tokens (int): Max tokens
    temperature (float): Temperature
    top_p (float): Top p
    model_id (str): Model ID
    
    Returns:
    str: Response
    """
    body = json.dumps({"prompt": prompt_data, "maxTokens": max_tokens, "temperature":temperature, "topP":top_p})
    modelId = model_id
    accept = 'application/json'
    contentType = 'application/json'

    bedrock_response = bedrock.invoke_model(body=body, modelId=modelId, accept=accept, contentType=contentType)
    response_body = json.loads(bedrock_response.get('body').read())
    return response_body.get('completions')[0].get('data').get('text')

# Set the page title and icon
st.set_page_config(
    page_title="Amazon Bedrock and AI21 Lab with Jurassic-2 Ultra model Personalized Email Promo",
    page_icon="https://neurons-lab-public-bucket.s3.eu-central-1.amazonaws.com/Logo.png",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("# Amazon Bedrock for Personalized Email Promo")

st.markdown("## Input Data")
st.markdown("### Promos")
promo = pd.read_csv('data/promo.csv')
st.dataframe(promo, width=1000)
st.markdown("### Customers")
st.markdown("Select the customers you want to send a personalized promo email.")
customers = pd.read_csv('data/customers.csv')

def dataframe_with_selections(df):
    """Adds a temporary column to a dataframe with checkboxes for row selection.
    Parameters:
    df (pandas.DataFrame): Dataframe to add selections to (will not be modified)

    Returns:
    (pandas.DataFrame): Dataframe filtered to only selected rows
    """
    df_with_selections = df.copy()
    df_with_selections.insert(0, "Select", False)

    # Get dataframe row-selections from user with st.data_editor
    edited_df = st.data_editor(
        df_with_selections,
        width=1000,
        hide_index=True,
        column_config={"Select": st.column_config.CheckboxColumn(required=True)},
        disabled=df.columns,

    )

    # Filter the dataframe using the temporary column, then drop the column
    selected_rows = edited_df[edited_df.Select]
    return selected_rows.drop('Select', axis=1)

selection = dataframe_with_selections(customers)
st.write("Your selection:")
st.dataframe(selection, width=1000)

with st.form("Identify Personalized Promos"):
    # Every form must have a submit button.
    submitted = st.form_submit_button("Submit")
    if submitted:
        for customer in selection.to_dict(orient='records'):
            with st.container():
                st.markdown("## Results")
                st.markdown("### Indentify Personalized Promo")
                st.markdown(f"**Customer Name:** {customer['name']}")
                promo_txt = ""
                for ind in promo.index:
                    promo_txt += f"{promo['PROMO NAME'][ind]}\n"

                promo_prompt = f"""Select only one (1) with reasoning the most relevant Promo that fit to Customer Interests: "{customer['interest']}" from Available Promos list.
Available Promos:
{promo_txt}
"""
                response = j2_invoke(promo_prompt, max_tokens=250)
                st.markdown(response)
            
            with st.container():
                st.markdown("### Create Personalized Email Promo")


                email_prompt = f"""You are Ron, Account Manager. You write a personalized email promo from Amazon.com.

Your task is to print only text of the email in Markdown with emoji.
Use a friendly and conversational tone. Include a personalized greeting with person's name.
Use the provided promo and highlight how they can bs useful for person in a clear and appealing way.
Use language that would resonate with age, gender and interests of the person. 
Close the email with a call to action to shop the sales and an expression of value for him as a customer.

The format of the email is Markdown with emoji. 
You do not use headers for the sections of the email, do not write any side comments or links, do not use images.
You must escape characters for Markdown, for example $, #, *, etc.

You customer name is {customer['name']}, age is {customer['age']}, gender is {customer['gender']}. 
The customer has interest: {customer['interest']}. Based on the interest, you have selected the personalized promo: {response}.
"""
                email_response = j2_invoke(email_prompt, max_tokens=3000)

                st.markdown(email_response)