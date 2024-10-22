import streamlit as st
import yaml
import itertools
import pandas as pd


# Function to load the OpenAPI spec from a YAML file
def load_openapi_spec(file):
    return yaml.safe_load(file)


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


# Function to resolve $ref references in the OpenAPI spec
def resolve_refs(openapi_dict, components):
    if isinstance(openapi_dict, dict):
        for key, value in openapi_dict.items():
            if key == "$ref":
                # Resolve the $ref by replacing it with the actual referenced schema
                ref_path = value.split('/')[-1]
                if ref_path in components:
                    return resolve_refs(components[ref_path], components)
            else:
                openapi_dict[key] = resolve_refs(value, components)
    elif isinstance(openapi_dict, list):
        return [resolve_refs(item, components) for item in openapi_dict]

    return openapi_dict


# Streamlit App
st.title("OpenAPI Spec API Explorer")

# File upload option
uploaded_file = st.file_uploader("Upload OpenAPI YAML file", type="yaml")

if uploaded_file:
    # Load the OpenAPI spec
    openapi_spec = load_openapi_spec(uploaded_file)

    # Extract components and resolve all references
    components = openapi_spec.get('components', {}).get('schemas', {})
    resolved_openapi_spec = resolve_refs(openapi_spec, components)

    # Get all possible API combinations from the resolved spec
    api_combinations_resolved = get_api_combinations(resolved_openapi_spec)

    # Convert the list of API combinations into a Pandas DataFrame
    df_api_combinations = pd.DataFrame(api_combinations_resolved)

    # Display the DataFrame in the Streamlit app
    st.subheader("API Combinations:")
    st.dataframe(df_api_combinations)

    # Option to download the DataFrame as a CSV file
    csv = df_api_combinations.to_csv(index=False)
    st.download_button(
        label="Download API Combinations as CSV",
        data=csv,
        file_name='api_combinations.csv',
        mime='text/csv',
    )
