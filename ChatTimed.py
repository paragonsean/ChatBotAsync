import json
import os

import requests
from requests import Response
import openmeteo_requests
import requests_cache
from openai import OpenAI
from openai.types.chat import ChatCompletion
from typing import Literal
import time
from dotenv import load_dotenv
load_dotenv(dotenv_path='.env')



api_key = os.getenv("OPENAI_API_KEY")
# Example prompts
PROMPTS = {
    "headsOrTails": ("To decide what to eat tonight, we want to flip a coin. At heads we'll eat pizza, at tails a "
                     "salad. What will we eat tonight?"),
    "rollDice": "Alice, Bob and Claire decide who gets to last ice cream by rolling a dice. The highest roller gets "
                "the ice cream. Please assist with this.",
    "trump": "Who is Donald Trump?",
    "willItRain": "Is there a chance of rain today in Amsterdam?",
    "tempZimbabwe": "how hot is it in Zimbabwe today?",
    "bbqWeather": "Is today a good day for bbq'ing in Antarctica?",
    "whichMonth": "Based on the weather in New York, what month do you think it is?"
}

randomNumbersTool = {
    "type": "function",
    "function": {
        "name": "get_random_numbers",
        "description": "Generates a list of random numbers",
        "parameters": {
            "type": "object",
            "properties": {
                "min": {
                    "type": "integer",
                    "description": "Lower bound on the generated number",
                },
                "max": {
                    "type": "integer",
                    "description": "Upper bound on the generated number",
                },
                "count": {
                    "type": "integer",
                    "description": "How many numbers should be calculated",
                }
            },
            "required": ["min", "max", "count"],
        }
    }
}

temperatureTool = {
    "type": "function",
    "function": {
        "name": "get_temperature",
        "description": "Gives the temperature for a given location",
        "parameters": {
            "type": "object",
            "properties": {
                "latitude": {
                    "type": "number",
                    "description": "The latitude of the location",
                },
                "longitude": {
                    "type": "number",
                    "description": "The longitude of the location",
                },
            },
            "required": ["latitude, longitude"],
        }
    }
}

def timer(func):
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        print(f"{func.__name__} took {end_time - start_time} seconds to execute.")
        return result
    return wrapper

@timer
def get_random_numbers(min: int, max: int, count: int) -> str:
    url = "http://www.randomnumberapi.com/api/v1.0/random"
    params = {
        'min': min,
        'max': max,
        'count': count
    }
    response = requests.get(url, params=params)
    return json.dumps({"random numbers": response.json()})

@timer
def get_temperature(latitude: float, longitude: float) -> str:
    cache_session = requests_cache.CachedSession('.cache', expire_after=3600)
    openmeteo = openmeteo_requests.Client(session=cache_session)

    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "current": "temperature_2m"
    }
    responses = openmeteo.weather_api(url, params=params)
    value = responses[0].Current().Variables(0).Value()
    return json.dumps({"temperature": str(value)})

@timer
def handle_tool_response(client: OpenAI, completion: ChatCompletion, messages: list[dict[str, str]]) -> str:
    tool_calls = completion.choices[0].message.tool_calls

    if tool_calls:
        tool_name = tool_calls[0].function.name
        if tool_name == 'get_random_numbers':
            args = json.loads(tool_calls[0].function.arguments)
            observation = get_random_numbers(**args)
            messages.append({
                "role": "function",
                "name": tool_name,
                "content": observation
            })
            response_with_function_call = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages,
            )
            return response_with_function_call.choices[0].message.content

        elif tool_name == 'get_temperature':
            args = json.loads(tool_calls[0].function.arguments)
            observation = get_temperature(**args)
            messages.append({
                "role": "function",
                "name": tool_name,
                "content": observation
            })
            response_with_function_call = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages,
            )
            return response_with_function_call.choices[0].message.content

        else:
            return "error: function call defined by model does not exist"

    return completion.choices[0].message.content

@timer
def callAsistantWithTools(tools, role: str, prompt: str) -> str:
    messages = [
        {"role": "system", "content": role},
        {"role": "user", "content": prompt}
    ]
    client = OpenAI()
    completion = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
        tools=tools,
        tool_choice="auto"
    )
    return handle_tool_response(client, completion, messages)

class MockFunction:
    arguments: list[object]
    name: str

    def __init__(self, arguments, name: str):
        self.arguments = arguments
        self.name = name

class MockToolCall:
    type: Literal['function', 'other']
    function: MockFunction

    def __init__(self, function: MockFunction, type):
        self.function: MockFunction = function
        self.type = type

class MockMessage:
    tool_calls: list[MockToolCall]
    content: str
    role: str

    def __init__(self, content, tool_calls: list[MockToolCall]):
        self.role = 'assistant'
        self.content = content
        self.tool_calls = tool_calls

class MockChoice:
    message: MockMessage

    def __init__(self, message):
        self.message = message

class MockCompletion:
    choices: list[MockChoice]

    def __init__(self, choices: list[MockChoice]):
        self.choices = choices

if __name__ == "__main__":
    tools = [randomNumbersTool, temperatureTool]
    role = "You assist me with calling specific tools to retrieve the temperature or generate random numbers."

    for prompt_key, prompt_text in PROMPTS.items():
        print(f"Processing prompt: {prompt_key}")
        response = callAsistantWithTools(tools, role, prompt_text)
        print(f"Response for '{prompt_key}': {response}\n")
