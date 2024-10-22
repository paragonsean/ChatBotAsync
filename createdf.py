import jsonref
import yaml
import pandas as pd
import itertools


# Load the OpenAPI spec from the YAML file and resolve $ref references using jsonref
def load_openapi_spec_with_jsonref(file_path):
    with open(file_path, 'r') as file:
        # Load the OpenAPI spec and resolve references automatically
        return jsonref.loads(yaml.safe_load(file), jsonschema=True)


# Function to extract all possible API calls from the OpenAPI spec
def get_api_combinations(openapi_spec):
    api_combinations = []

    # Loop over all paths in the OpenAPI spec
    for path, methods in openapi_spec.get('paths', {}).items():
        # For each path, iterate over the available methods (GET, POST, etc.)
        for method, details in methods.items():
            if isinstance(details, dict):
                # Extract parameters, request bodies, and responses for each method
                parameters = details.get('parameters', [])
                request_body = details.get('requestBody', 'No request body.')
                responses = details.get('responses', 'No responses specified.')

                # If parameters exist, generate all possible combinations
                if parameters:
                    param_combinations = get_parameter_combinations(parameters)
                    # For each parameter combination, create an API call entry
                    for param_combo in param_combinations:
                        api_combinations.append({
                            'Path': path,
                            'Method': method.upper(),
                            'Parameters': param_combo,
                            'Request Body': request_body,
                            'Responses': responses
                        })
                else:
                    # If no parameters, just create a single API call entry
                    api_combinations.append({
                        'Path': path,
                        'Method': method.upper(),
                        'Parameters': 'No parameters specified.',
                        'Request Body': request_body,
                        'Responses': responses
                    })

    return api_combinations


# Function to generate all possible parameter combinations
def get_parameter_combinations(parameters):
    param_values = []

    # Iterate over each parameter and create a list of possible values
    for param in parameters:
        param_name = param.get('name', 'Unnamed parameter')
        param_type = param.get('schema', {}).get('type', 'string')
        param_enum = param.get('schema', {}).get('enum', [])

        # If the parameter has enumerated values, use them, otherwise, create placeholders
        if param_enum:
            param_values.append([(param_name, value) for value in param_enum])
        else:
            param_values.append([(param_name, f'<{param_type}>')])

    # Create all possible combinations of parameters using itertools.product
    return [dict(combo) for combo in itertools.product(*param_values)]


# Example usage:
file_path = 'openapi.yaml'  # Path to your OpenAPI spec
openapi_spec = load_openapi_spec_with_jsonref(file_path)

# Extract the API combinations
api_combinations = get_api_combinations(openapi_spec)

# Convert to a Pandas DataFrame for better readability
df_api_combinations = pd.DataFrame(api_combinations)

# Display the DataFrame
print(df_api_combinations)
