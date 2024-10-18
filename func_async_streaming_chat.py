import json
import os
import functools
import time
from loguru import logger  # Importing loguru
import aiohttp
import openmeteo_requests
import requests_cache
from openai import AsyncOpenAI
from typing import Literal
import asyncio
from dotenv import load_dotenv

load_dotenv(dotenv_path='.env')
api_key = os.getenv("OPENAI_API_KEY")

# Example prompts
logger.add(sys.stdout, format="{time} {level} {message}\n", level="INFO")  # Configure loguru to add a newline


def log_function_call(func):
    """Log Function Call with Duration using loguru."""

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        logger.info(f"Calling function: {func.__name__} with args: {args} and kwargs: {kwargs}\n")
        start_time = time.time()

        if asyncio.iscoroutinefunction(func):
            @functools.wraps(func)
            async def async_wrapper(*args, **kwargs):
                result = await func(*args, **kwargs)
                end_time = time.time()
                duration = end_time - start_time
                logger.info(f"Function {func.__name__} completed with result: {result} in {duration:.4f} seconds\n")
                return result

            return async_wrapper(*args, **kwargs)
        else:
            result = func(*args, **kwargs)
            end_time = time.time()
            duration = end_time - start_time
            logger.info(f"Function {func.__name__} completed with result: {result} in {duration:.4f} seconds\n")
            return result

    return wrapper


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
            "required": ["latitude", "longitude"],
        }
    }
}


@log_function_call
async def get_random_numbers(min: int, max: int, count: int) -> str:
    url = "http://www.randomnumberapi.com/api/v1.0/random"
    params = {
        'min': min,
        'max': max,
        'count': count
    }
    async with aiohttp.ClientSession() as session:
        async with session.get(url, params=params) as response:
            return json.dumps({"random numbers": await response.json()})


@log_function_call
async def get_temperature(latitude: float, longitude: float) -> str:
    cache_session = requests_cache.CachedSession('.cache', expire_after=3600)
    openmeteo = openmeteo_requests.Client(session=cache_session)

    params = {
        "latitude": latitude,
        "longitude": longitude,
        "current_weather": True
    }

    response = await openmeteo.weather(params=params)
    value = response['current_weather']['temperature']
    return json.dumps({"temperature": str(value)})


@log_function_call
async def handle_tool_response(client: AsyncOpenAI, completion, messages: list[dict[str, str]]) -> str:
    tool_calls = completion.choices[0].message.function_call  # Access the function_call directly

    if tool_calls:
        tool_name = tool_calls['name']
        if tool_name == 'get_random_numbers':
            args = json.loads(tool_calls['arguments'])
            observation = await get_random_numbers(**args)
            messages.append({
                "role": "function",
                "name": tool_name,
                "content": observation
            })
            response_with_function_call = await client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages,
            )
            return response_with_function_call.choices[0].message['content']

        elif tool_name == 'get_temperature':
            args = json.loads(tool_calls['arguments'])
            observation = await get_temperature(**args)
            messages.append({
                "role": "function",
                "name": tool_name,
                "content": observation
            })
            response_with_function_call = await client.chat.completions.create(
                model="gpt-4o-mini",

