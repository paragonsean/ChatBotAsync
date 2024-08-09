import json
import aiohttp
import openmeteo_requests
import requests_cache
from openai import AsyncOpenAI
from typing import Literal
import asyncio

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

async def get_temperature(latitude: float, longitude: float) -> str:
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

async def handle_tool_response(client: AsyncOpenAI, completion, messages: list[dict[str, str]]) -> str:
    tool_calls = completion.choices[0].message.tool_calls

    if tool_calls:
        tool_name = tool_calls[0].function.name
        if tool_name == 'get_random_numbers':
            args = json.loads(tool_calls[0].function.arguments)
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
            return response_with_function_call.choices[0].message.content

        elif tool_name == 'get_temperature':
            args = json.loads(tool_calls[0].function.arguments)
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
            return response_with_function_call.choices[0].message.content

        else:
            return "error: function call defined by model does not exist"

    return completion.choices[0].message.content

async def callAsistantWithTools(tools, role: str, prompt: str) -> str:
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
    response = asyncio.run(callAsistantWithTools(tools, "You assist me with calling specific tools to retrieve the temperature or generate random numbers.", prompt=PROMPTS["bbqWeather"]))
    print(response)
