#    ___              __         ____    __      __  ___         __                     __
#   / _ \___ ___ ____/ /_ __    / __/__ / /_    /  |/  /__  ____/ /____ ____ ____ ____ / /
#  / , _/ -_) _ `/ _  / // /   _\ \/ -_) __/   / /|_/ / _ \/ __/ __/ _ `/ _ `/ _ `/ -_)_/ 
# /_/|_|\__/\_,_/\_,_/\_, ( ) /___/\__/\__( ) /_/  /_/\___/_/  \__/\_, /\_,_/\_, /\__(_)  
#                    /___/|/              |/                      /___/     /___/ 
#
# Ready, Set, Mortgage! API
# Authors: 

#-------------#
#   IMPORTS   #
#-------------#

import os
from dotenv import load_dotenv
from typing import Annotated
from fastapi import Body,FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import openai


#------------------------#
#   INITIALIZE FASTAPI   #
#------------------------#

app = FastAPI()                                     # Creates FastAPI App
origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)                                                   # Allows cross-origin requests


#-----------------------#
#   INITIALIZE OPENAI   #
#-----------------------#

load_dotenv()                                       # Loads environment variables from a .env file if present for local development
OPENAI_KEY = os.getenv('OPENAI_KEY')                # Imports OpenAI key from environment variable


#-----------------------#
#   DEFINE DATA MODEL   #
#-----------------------#

class UserStats(BaseModel):
    gross_monthly_income: float
    monthly_car_payment: float
    monthly_credit_card_payment: float
    student_loan_payment: float
    home_appraised_value: float
    est_monthly_mortgage_payment: float
    down_payment_amount: float
    credit_score: int


#---------------------------#
#   SANITY CHECK ENDPOINT   #
#---------------------------#

@app.get("/")                                       # Sanity check endpoint to ensure server is accessible
async def sanity_check():
    return {
        "message": "Welcome to Ready, Set, Mortgage's API! To read more about the available endpoints, visit https://api.readysetmortgage.co/docs"
    }


#---------------------------------#
#   MORTGAGE READINESS ENDPOINT   #
#---------------------------------#

@app.post("/readiness")
async def readiness(userstats: UserStats):                                  # Declares an empty List of notices
    return determine_response(userstats)


#--------------------------#
#   AI FEEDBACK ENDPOINT   #
#--------------------------#

@app.post("/ai_feedback")
async def ai_feedback(userstats: UserStats):
    return {
        'response': 'Placeholder'
    }

#----------------------#
#   HELPER FUNCTIONS   #
#----------------------#

def calculate_monthly_debt(monthly_car_payment: float, monthly_credit_card_payment: float, est_monthly_mortgage_payment: float, student_loan_payment: float) -> float:
    return monthly_car_payment + monthly_credit_card_payment + est_monthly_mortgage_payment + student_loan_payment

def calculate_ltv(home_appraised_value: float, down_payment_amount: float) -> float:
    return (home_appraised_value - down_payment_amount) / home_appraised_value

def calculate_dti(monthly_debt: float, gross_monthly_income: float) -> float:
    return monthly_debt / gross_monthly_income

def calculate_fedti(est_monthly_mortgage_payment: float, gross_monthly_income: float) -> float:
    return est_monthly_mortgage_payment / gross_monthly_income

def compare_ltv(ltv: float) -> str:
    if ltv < 0.80:
        return 'Y'
    elif ltv <= 0.95:
        return 'M'
    else:
        return 'N'

def compare_dti(dti: float) -> str:
    if dti <= 0.36:
        return 'Y'
    elif dti <= 0.43:
        return 'M'
    else:
        return 'N'

def compare_fedti(fedti: float) -> str:
    if fedti <= 28:
        return 'Y'
    else:
        return 'N'

def compare_credit(credit_score) -> str:
    if credit_score >= 640:
        return 'Y'
    else:
        return 'N'

def compare_readiness(credit_score, dti, ltv, fedti):
    individual_readiness = {
        'credit': compare_credit(credit_score),
        'ltv': compare_ltv(ltv),
        'dti': compare_dti(dti),
        'fedti': compare_fedti(fedti)
    }

    if 'N' in individual_readiness.values():
        return 'N'
    elif 'M' in individual_readiness.values():
        return 'M'
    else:
        return 'Y'


def assess_notices(credit_score, dti, ltv, fedti) -> list:
    individual_readiness = {
        'credit': compare_credit(credit_score),
        'ltv': compare_ltv(ltv),
        'dti': compare_dti(dti),
        'fedti': compare_fedti(fedti)
    }

    notices = []

    if individual_readiness['credit'] == 'N':
        notices.append("Your credit score is too low. Lenders will generally only accept a credit score greater than 640")
    
    if individual_readiness['ltv'] == 'N':
        notices.append("The ratio of your loan amount to the house's value is very high. Loan-to-value ratios above 95\% tend to be rejected by lenders. Consider increasing your down payment.")
    elif individual_readiness['ltv'] == 'M':
        notices.append("The ratio of your loan amount to the house's value is moderately high. Loan-to-value ratios between 80% and 95\% tend to result in higher interest rates and may require you to purchase private mortgage insurance. Consider increasing your down payment.")
    
    if individual_readiness['dti'] == 'N':
        notices.append("Your ratio of debt to income is too high to be accepted by a lender. The highest ratio any lender will take is 43\%, but most lenders prefer a ratio of 36% or less.")
    elif individual_readiness['dti'] == 'M':
        notices.append("Your ratio of debt to income is moderately high. While some lenders may accept it, most lenders prefer a debt-to-income ratio of 36% or less.")
    
    if individual_readiness['fedti'] == 'N':
        notices.append("The percentage of that debt going toward mortgages, your \"front-end debt\", is too high to be considered for a loan. Generally, the ratio of your front-end debt to income should not exceed 28%.")
    
    return notices

def determine_response(userstats: UserStats) -> dict:
    monthly_debt = calculate_monthly_debt(userstats.monthly_car_payment, userstats.monthly_credit_card_payment, userstats.est_monthly_mortgage_payment, userstats.student_loan_payment)
    credit_score = userstats.credit_score
    ltv = calculate_ltv(userstats.home_appraised_value, userstats.down_payment_amount)
    dti = calculate_dti(monthly_debt, userstats.gross_monthly_income)
    fedti = calculate_fedti(userstats.est_monthly_mortgage_payment, userstats.gross_monthly_income)
    notices = assess_notices(credit_score, dti, ltv, fedti)

    return {
        'readiness': compare_readiness(credit_score, dti, ltv, fedti),
        'breakdown': {
            'credit': {
                'individual_readiness': compare_credit(credit_score),
                'score': credit_score
            },
            'ltv': {
                'individual_readiness': compare_ltv(ltv),
                'score': ltv
            },
            'dti': {
                'individual_readiness': compare_dti(dti),
                'score': dti
            },
            'fedti': {
                'individual_readiness': compare_fedti(fedti),
                'score': fedti
            }
        },
        'notices': notices
    }
