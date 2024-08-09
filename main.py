from prompts import PROMPTS
from src.callAsistant import callAsistantWithTools
from src.tools.toolSchemas import randomNumbersTool, temperatureTool

# Provide the model with schema definitions of helper functions to ask the temperature and to generate random numbers
tools = [
    randomNumbersTool,
    temperatureTool
]

print(callAsistantWithTools(tools,
                            "You assist me with calling specific tools to retrieve the temperature or generate " \
                            "random numbers.",
                            prompt=PROMPTS["bbqWeather"]))
