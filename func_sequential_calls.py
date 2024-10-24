import json
import math
import pandas as pd
import pytz
from datetime import datetime
from utils import check_args, setup_client
from loguru import logger
import requests

# Set up the OpenAI client, get the deployment name
client, DEPLOYMENT_NAME = setup_client()

def get_current_time(location):
    try:
        timezone = pytz.timezone(location)
        now = datetime.now(timezone)
        current_time = now.strftime("%I:%M:%S %p")
        return current_time
    except Exception as e:
        logger.error(f"Failed to get timezone for location '{location}': {e}")
        return "Sorry, I couldn't find the timezone for that location."

def get_stock_market_data(index, start_date=None, end_date=None):
    available_indices = [
        "Natural_Gas_Price", "Natural_Gas_Vol.", "Crude_oil_Price", "Crude_oil_Vol.",
        "Copper_Price", "Copper_Vol.", "Bitcoin_Price", "Bitcoin_Vol.", "Platinum_Price", 
        "Platinum_Vol.", "Ethereum_Price", "Ethereum_Vol.", "S&P_500_Price", "Nasdaq_100_Price",
        "Nasdaq_100_Vol.", "Apple_Price", "Apple_Vol.", "Tesla_Price", "Tesla_Vol.", 
        "Microsoft_Price", "Microsoft_Vol.", "Silver_Price", "Silver_Vol.", "Google_Price", 
        "Google_Vol.", "Nvidia_Price", "Nvidia_Vol.", "Berkshire_Price", "Berkshire_Vol.", 
        "Netflix_Price", "Netflix_Vol.", "Amazon_Price", "Amazon_Vol.", "Meta_Price", 
        "Meta_Vol.", "Gold_Price", "Gold_Vol."
    ]

    if index not in available_indices:
        logger.warning(f"Invalid index provided: {index}")
        return f"Invalid index. Please choose from available indices: {', '.join(available_indices)}"

    try:
        # Load the CSV file and ensure 'Date' is parsed as a datetime object with specified format
        data = pd.read_csv('data/Stock Market Dataset.csv', parse_dates=["Date"], dayfirst=True)
        
        # Convert start_date and end_date to Timestamps for proper comparison
        if start_date:
            start_date = pd.to_datetime(start_date, errors='coerce')
        if end_date:
            end_date = pd.to_datetime(end_date, errors='coerce')

        # Validate that dates are properly parsed
        if start_date is pd.NaT or end_date is pd.NaT:
            return "Invalid date format. Please use YYYY-MM-DD."

        # Filter data for the given index and optional date range
        if start_date and end_date:
            # Ensure the 'Date' column and the provided dates are of the same type (datetime)
            mask = (data["Date"] >= start_date) & (data["Date"] <= end_date)
            data_filtered = data.loc[mask, ["Date", index]]
        else:
            data_filtered = data[["Date", index]]
        
        # Check if the filtered data is empty
        if data_filtered.empty:
            return f"No data available for index '{index}' in the given date range."

        # Convert the DataFrame into a dictionary (Date as key, index values as values)
        data_filtered["Date"] = data_filtered["Date"].dt.strftime('%Y-%m-%d')
        data_dict = data_filtered.set_index("Date")[index].to_dict()
        
        return json.dumps(data_dict, indent=4)
    
    except Exception as e:
        logger.error(f"Failed to retrieve stock data for index '{index}': {e}")
        return "Error in retrieving stock data."



def calculator(num1, num2, operator):
    try:
        if operator == "+":
            result = num1 + num2
        elif operator == "-":
            result = num1 - num2
        elif operator == "*":
            result = num1 * num2
        elif operator == "/":
            result = num1 / num2
        elif operator == "**":
            result = num1 ** num2
        elif operator == "sqrt":
            result = math.sqrt(num1)
        else:
            logger.warning(f"Invalid operator provided: {operator}")
            return "Invalid operator"

        logger.info(f"Calculation result: {num1} {operator} {num2} = {result}")
        return str(result)
    except Exception as e:
        logger.error(f"Error in calculation: {e}")
        return "Error in calculation."

def get_temperature(latitude: float, longitude: float) -> str:
    try:
        url = "https://api.open-meteo.com/v1/forecast"
        params = {
            "latitude": latitude,
            "longitude": longitude,
            "current_weather": True
        }
        response = requests.get(url, params=params)
        response.raise_for_status()

        weather_data = response.json()
        temperature = weather_data.get("current_weather", {}).get("temperature", "N/A")
        return json.dumps({"temperature": temperature}, indent=4)
    except Exception as e:
        logger.error(f"Failed to fetch temperature: {e}")
        return "Error in retrieving temperature."

def get_historical_temperature(latitude: float, longitude: float, start_date: str, end_date: str) -> str:
    try:
        url = "https://archive-api.open-meteo.com/v1/archive"
        params = {
            "latitude": latitude,
            "longitude": longitude,
            "start_date": start_date,
            "end_date": end_date,
            "daily": "temperature_2m_max,temperature_2m_min",
            "timezone": "auto"
        }
        response = requests.get(url, params=params)
        response.raise_for_status()

        weather_data = response.json()
        temperature_data = weather_data.get("daily", {})
        return json.dumps({"temperature_data": temperature_data}, indent=4)
    except Exception as e:
        logger.error(f"Failed to fetch historical temperature data: {e}")
        return "Error in retrieving historical temperature data."

def calculate_difference(index, date1, date2):
    try:
        data = pd.read_csv('/mnt/data/Stock Market Dataset.csv', parse_dates=["Date"])
        data_filtered = data[data["Date"].isin([pd.to_datetime(date1), pd.to_datetime(date2)])]
        
        if data_filtered.empty or len(data_filtered) < 2:
            return "Insufficient data to calculate difference."
        
        price1 = data_filtered[data_filtered["Date"] == pd.to_datetime(date1)][index].values[0]
        price2 = data_filtered[data_filtered["Date"] == pd.to_datetime(date2)][index].values[0]
        
        difference = price2 - price1
        return json.dumps({"difference": difference}, indent=4)
    except Exception as e:
        logger.error(f"Failed to calculate difference for index '{index}': {e}")
        return "Error in calculating difference."

def get_tools():
    return [
        {
            "type": "function",
            "function": {
                "name": "get_current_time",
                "description": "Get the current time in a given location",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "location": {
                            "type": "string",
                            "description": "The location name. The pytz is used to get the timezone for that location.",
                        }
                    },
                    "required": ["location"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "get_stock_market_data",
                "description": "Get the stock market data for a given index and optional date range",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "index": {
                            "type": "string",
                            "enum": [
                                "Natural_Gas_Price", "Natural_Gas_Vol.", "Crude_oil_Price", "Crude_oil_Vol.",
                                "Copper_Price", "Copper_Vol.", "Bitcoin_Price", "Bitcoin_Vol.", "Platinum_Price", 
                                "Platinum_Vol.", "Ethereum_Price", "Ethereum_Vol.", "S&P_500_Price", "Nasdaq_100_Price",
                                "Nasdaq_100_Vol.", "Apple_Price", "Apple_Vol.", "Tesla_Price", "Tesla_Vol.", 
                                "Microsoft_Price", "Microsoft_Vol.", "Silver_Price", "Silver_Vol.", "Google_Price", 
                                "Google_Vol.", "Nvidia_Price", "Nvidia_Vol.", "Berkshire_Price", "Berkshire_Vol.", 
                                "Netflix_Price", "Netflix_Vol.", "Amazon_Price", "Amazon_Vol.", "Meta_Price", 
                                "Meta_Vol.", "Gold_Price", "Gold_Vol."
                            ],
                        },
                        "start_date": {
                            "type": "string",
                            "description": "The start date for the data (in YYYY-MM-DD format). Optional.",
                        },
                        "end_date": {
                            "type": "string",
                            "description": "The end date for the data (in YYYY-MM-DD format). Optional.",
                        }
                    },
                    "required": ["index"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "calculator",
                "description": "A simple calculator used to perform basic arithmetic operations",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "num1": {"type": "number"},
                        "num2": {"type": "number"},
                        "operator": {
                            "type": "string",
                            "enum": ["+", "-", "*", "/", "**", "sqrt"],
                        },
                    },
                    "required": ["num1", "num2", "operator"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "get_temperature",
                "description": "Gives the current temperature for a given location.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "latitude": {
                            "type": "number",
                            "description": "The latitude of the location."
                        },
                        "longitude": {
                            "type": "number",
                            "description": "The longitude of the location."
                        }
                    },
                    "required": ["latitude", "longitude"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "get_historical_temperature",
                "description": "Fetches the historical temperature data for a given location and date range.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "latitude": {
                            "type": "number",
                            "description": "The latitude of the location."
                        },
                        "longitude": {
                            "type": "number",
                            "description": "The longitude of the location."
                        },
                        "start_date": {
                            "type": "string",
                            "description": "The start date for the historical data (in YYYY-MM-DD format)."
                        },
                        "end_date": {
                            "type": "string",
                            "description": "The end date for the historical data (in YYYY-MM-DD format)."
                        }
                    },
                    "required": ["latitude", "longitude", "start_date", "end_date"]
                }
            }
        }
    ]

def get_available_functions():
    return {
        "get_current_time": get_current_time,
        "get_stock_market_data": get_stock_market_data,
        "calculator": calculator,
        "get_temperature": get_temperature,
        "get_historical_temperature": get_historical_temperature
    }

def run_multiturn_conversation(messages, tools, available_functions):
    response = client.chat.completions.create(
        model=DEPLOYMENT_NAME,
        messages=messages,
        tools=tools,
        tool_choice="auto",
        temperature=0,
    )

    while response.choices[0].finish_reason == "tool_calls":
        response_message = response.choices[0].message

        # Log only the function being called
        function_name = response_message.tool_calls[0].function.name
        logger.info(f"Calling function: {function_name}")

        if function_name not in available_functions:
            return f"Function {function_name} does not exist"
        
        function_to_call = available_functions[function_name]
        function_args = json.loads(response_message.tool_calls[0].function.arguments)

        if not check_args(function_to_call, function_args):
            return f"Invalid number of arguments for function: {function_name}"

        # Call the function
        function_response = function_to_call(**function_args)

        # Add the function call and response to the messages
        messages.append({
            "role": response_message.role,
            "function_call": {
                "name": function_name,
                "arguments": response_message.tool_calls[0].function.arguments,
            },
            "content": None,
        })

        messages.append({
            "role": "function",
            "name": function_name,
            "content": function_response,
        })

        # Trim messages to avoid exceeding token limit
        messages = trim_messages(messages)

        # Make the next API call
        response = client.chat.completions.create(
            model=DEPLOYMENT_NAME,
            messages=messages,
            tools=tools,
            tool_choice="auto",
            temperature=0,
        )

    return response

def trim_messages(messages, max_tokens=29000):
    """
    Trims the message history to ensure the token count stays below the max_tokens limit.
    This is a simplistic approach and can be enhanced with proper token counting.
    """
    # Estimate tokens by counting words (rough approximation)
    current_tokens = 0
    trimmed_messages = []
    for message in reversed(messages):
        message_length = len(message["content"].split()) if message["content"] else 0
        if current_tokens + message_length > max_tokens:
            break
        trimmed_messages.insert(0, message)
        current_tokens += message_length
    return trimmed_messages

# Get the user's question as input
user_question = input("Please enter your question: ")

next_messages = [
    {
        "role": "system",
        "content": "Assistant is a helpful assistant that helps users get answers to questions. Assistant has access to several tools and sometimes you may need to call multiple tools in sequence to get answers for your users.",
    }
]
next_messages.append(
    {
        "role": "user",
        "content": user_question,
    }
)

logger.info("Starting the conversation")
assistant_response = run_multiturn_conversation(
    next_messages, get_tools(), get_available_functions()
)

print(assistant_response.choices[0].message.content)
