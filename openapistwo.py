import click
import json
import requests
from openapi_client import ApiClient, Configuration, ApiException  # Adjust based on your generated client

@click.command()
@click.option('--operation', '-o', help='Operation ID to call')
@click.option('--param', '-p', multiple=True, help='Parameters for the request in key=value format')
@click.option('--data', '-d', help='Request body in JSON format')
@click.option('--include', '-i', is_flag=True, help='Include status code and response headers in the output')
@click.option('--verbose', '-v', is_flag=True, help='Verbose mode')
@click.option('--server', '-s', help='Server URL to use for the API', default='https://petstore3.swagger.io/api/v3')
@click.option('--spec-url', '-u', help='URL to fetch the OpenAPI spec', required=True)
@click.option('--inspect', is_flag=True, help='Inspect available operations from the OpenAPI spec')
def call_api(operation, param, data, include, verbose, server, spec_url, inspect):
    """Fetch the OpenAPI spec and interact with API operations"""

    # Fetch the OpenAPI spec from the provided URL
    try:
        response = requests.get(spec_url)
        response.raise_for_status()  # Check if the request was successful
        openapi_spec = response.json()
        click.echo("OpenAPI spec fetched successfully")
    except requests.RequestException as e:
        click.echo(f"Error fetching OpenAPI spec: {e}", err=True)
        return

    # Inspect mode - list available operations
    if inspect:
        if 'paths' not in openapi_spec:
            click.echo("No paths found in the OpenAPI spec", err=True)
            return

        click.echo("Available operations:")
        for path, methods in openapi_spec['paths'].items():
            for method, operation in methods.items():
                operation_id = operation.get('operationId', 'N/A')
                summary = operation.get('summary', 'No summary provided')
                click.echo(f"{method.upper()} {path} - {operation_id}: {summary}")
        return

    # If not inspecting, interact with API
    if not operation:
        click.echo("Operation ID is required to interact with the API. Use --operation or --inspect to list available operations.", err=True)
        return

    # Initialize the API client
    configuration = Configuration()
    configuration.host = server
    client = ApiClient(configuration)

    # Parse params into a dictionary
    params = {}
    if param:
        for p in param:
            key, value = p.split('=')
            params[key] = value

    # Convert request body to a dictionary
    request_body = {}
    if data:
        try:
            request_body = json.loads(data)
        except json.JSONDecodeError:
            click.echo('Invalid JSON format for request body', err=True)
            return

    # Dynamically retrieve the operation method
    # Example: using PetApi for Petstore API - replace with the actual API class
    api_instance = None
    for path, methods in openapi_spec['paths'].items():
        for method, op in methods.items():
            if op.get('operationId') == operation:
                api_instance = getattr(client, operation, None)

    if not api_instance:
        click.echo(f'Invalid operation ID: {operation}', err=True)
        return

    # Execute the API request
    try:
        response = api_instance(**params, **request_body)

        if include:
            click.echo(f'Status Code: {response.status_code}')
            click.echo(f'Response Headers: {response.headers}')

        click.echo(f'Response Body: {response.data}')

    except ApiException as e:
        click.echo(f"Exception when calling {operation}: {e}", err=True)
    except Exception as err:
        click.echo(f'Error occurred: {err}', err=True)

if __name__ == '__main__':
    call_api()