import boto3
import streamlit as st
import inspect
import textwrap


def get_openai_api_key(ssm_client, parameter_path):
    '''Get the OpenAI API key from the SSM Parameter Store'''
    try:
        response = ssm_client.get_parameter(
            Name=parameter_path,
            WithDecryption=True,
        )
        return response['Parameter']['Value']
    except ssm_client.exceptions.ParameterNotFound:
        raise Exception(f'Parameter {parameter_path} not found in SSM Parameter Store')


def show_code(demo):
    """Showing the code of the demo."""
    show_code = st.sidebar.checkbox('Show code', True)
    if show_code:
        # Showing the code of the demo.
        st.markdown('## Code')
        sourcelines, _ = inspect.getsourcelines(demo)
        st.code(textwrap.dedent(''.join(sourcelines[1:])))