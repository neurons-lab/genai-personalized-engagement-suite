"""AWS CDK Deploy Script"""
import os
from aws_cdk import (
    App,
    Aspects,
    Environment,
)

from stack.app_stack import AppStack

from cdk_nag import AwsSolutionsChecks, HIPAASecurityChecks
from dotenv import load_dotenv
load_dotenv('.env.sample', override=False)
load_dotenv('.env', override=True)


# App
app = App()
# Aspects.of(app).add(HIPAASecurityChecks(verbose=True,reports=True))
# Aspects.of(app).add(AwsSolutionsChecks(verbose=True,reports=True))


# Stack
AppStack(
    app, os.getenv('STACK_NAME', 'GenAiPESuiteStack'),
    env=Environment(
        account=os.getenv('AWS_ACCOUNT_ID', os.getenv('CDK_DEFAULT_ACCOUNT')),
        region=os.getenv('AWS_DEFAULT_REGION', os.getenv('CDK_DEFAULT_REGION'))
    ))

# Synth
app.synth()
