import click
import requests
import json


@click.command()
@click.option('--spec-url', '-u', help='URL to fetch the OpenAPI spec', required=True)
@click.option('--verbose', '-v', is_flag=True, help='Verbose mode')
def interactive_openapi(spec_url, verbose):
    """Dynamically load and interact with OpenAPI operations, including pagination"""

    # Fetch OpenAPI spec
    try:
        response = requests.get(spec_url)
        response.raise_for_status()  # Check for any request issues
        openapi_spec = response.json()
        click.echo("OpenAPI spec loaded successfully!")
    except requests.RequestException as e:
        click.echo(f"Failed to fetch OpenAPI spec: {e}", err=True)
        return

    # Validate spec contains paths
    if 'paths' not in openapi_spec:
        click.echo("No paths found in the OpenAPI spec!", err=True)
        return

    # Display available operations
    operations = {}
    click.echo("\nAvailable API Operations:")
    for path, methods in openapi_spec['paths'].items():
        for method, operation in methods.items():
            operation_id = operation.get('operationId', 'N/A')
            summary = operation.get('summary', 'No summary provided')
            operations[operation_id] = {
                'path': path,
                'method': method.upper(),
                'summary': summary,
                'parameters': operation.get('parameters', []),
                'requestBody': operation.get('requestBody', {})
            }
            click.echo(f"- {operation_id}: {summary} [{method.upper()} {path}]")

    # Prompt user for operation to execute
    operation_id = click.prompt("\nEnter the operationId of the API to call", type=str)
    if operation_id not in operations:
        click.echo(f"Invalid operationId: {operation_id}", err=True)
        return

    selected_operation = operations[operation_id]
    click.echo(f"\nSelected Operation: {operation_id} [{selected_operation['method']} {selected_operation['path']}]")

    # Prompt for parameters (if any)
    params = {}
    if selected_operation['parameters']:
        click.echo("\nProvide values for the following parameters:")
        for param in selected_operation['parameters']:
            param_name = param['name']
            param_required = param.get('required', False)
            param_value = click.prompt(f"  {param_name} (Required: {param_required})",
                                       default=None if not param_required else "")
            if param_value:
                params[param_name] = param_value

    # Prompt for request body (if any)
    data = None
    if 'content' in selected_operation['requestBody']:
        click.echo("\nProvide JSON request body:")
        data = click.edit(json.dumps({}, indent=2))
        if data:
            try:
                data = json.loads(data)
            except json.JSONDecodeError:
                click.echo("Invalid JSON format in request body!", err=True)
                return

    # Execute the API request with pagination handling
    full_url = spec_url.split('/openapi.json')[0] + selected_operation['path']
    headers = {'Content-Type': 'application/json'}

    # Handle Pagination
    results = []
    try:
        while True:
            if selected_operation['method'] == 'GET':
                res = requests.get(full_url, params=params, headers=headers)
            elif selected_operation['method'] == 'POST':
                res = requests.post(full_url, params=params, json=data, headers=headers)
            elif selected_operation['method'] == 'PUT':
                res = requests.put(full_url, params=params, json=data, headers=headers)
            elif selected_operation['method'] == 'DELETE':
                res = requests.delete(full_url, params=params, headers=headers)
            else:
                click.echo(f"Method {selected_operation['method']} not supported!", err=True)
                return

            res.raise_for_status()
            results.extend(res.json())

            # Check for pagination (e.g., 'next' URL or other pagination mechanisms)
            pagination = None
            if 'next' in res.links:
                pagination = res.links['next']['url']
            elif 'next' in res.json():
                pagination = res.json().get('next')

            if not pagination:
                break  # Exit loop if no more pages
            else:
                full_url = pagination  # Set next page URL

        click.echo(f"\nTotal results fetched: {len(results)}")
        click.echo(json.dumps(results, indent=2))

    except requests.RequestException as e:
        click.echo(f"API call failed: {e}", err=True)


if __name__ == '__main__':
    interactive_openapi()
