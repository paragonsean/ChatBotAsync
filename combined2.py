import json
import os
import functools
import time
import logging
import aiohttp
import openmeteo_requests

from openai import AsyncOpenAI
from typing import Literal
import asyncio
from dotenv import load_dotenv


# Example prompts
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

def log_function_call(func, debug=True):
    """Log Function Call with Duration."""
    if debug:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            logger.info(f"Calling function: {func.__name__} with args: {args} and kwargs: {kwargs} \n")
            start_time = time.time()

            if asyncio.iscoroutinefunction(func):
                @functools.wraps(func)
                async def async_wrapper(*args, **kwargs):
                    result = await func(*args, **kwargs)
                    end_time = time.time()
                    duration = end_time - start_time
                    logger.info(f"Function {func.__name__} completed with result: {result} in {duration:.4f} seconds \n")
                    return result

                return async_wrapper(*args, **kwargs)
            else:
                result = func(*args, **kwargs)
                end_time = time.time()
                duration = end_time - start_time
                logger.info(f"Function {func.__name__} completed with result: {result} in {duration:.4f} seconds \n")
                return result

        return wrapper
    else:
        return func


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

    openmeteo = openmeteo_requests.Client()

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
                messages=messages,
            )
            return response_with_function_call.choices[0].message['content']

        else:
            return "error: function call defined by model does not exist"

    return completion.choices[0].message['content']

@log_function_call
async def call_assistant_with_tools(tools, role: str, prompt: str) -> str:
    messages = [
        {"role": "system", "content": role},
        {"role": "user", "content": prompt}
    ]
    client = AsyncOpenAI()
    completion = await client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
        tools=tools,
        tool_choice="auto"
    )
    return await handle_tool_response(client, completion, messages)

if __name__ == "__main__":
    tools = [randomNumbersTool, temperatureTool]
    for prompt_name, prompt in PROMPTS.items():
        logger.info(f"Processing prompt: {prompt_name}")
        response = asyncio.run(call_assistant_with_tools(tools, "You assist me with calling specific tools to retrieve the temperature or generate random numbers.", prompt=prompt))
        print(f"Response for {prompt_name}: {response}")
