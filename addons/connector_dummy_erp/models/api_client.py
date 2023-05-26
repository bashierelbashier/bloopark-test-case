import requests


def get_headers():
    """
    Return default API headers
    :return: dict: headers dictionary
    """
    return {
        "Content-Type": "application/json",
    }


def get_request_url(integration, path):
    """Compose the request URL

    Args:
        integration (object): the dummy.erp.integration object
        path (str): path to the endpoint

    Returns:
        str: full URL for the http request
    """
    return integration._get_base_url() + path


def perform_request(integration, method, payload, path, add_headers=None):
    """Send HTTP request with given params

    Args:
        integration (object): dummy.erp.integration object
        method (str): HTTP method PUT, POST, ..
        payload (dict): payload
        path (str): path to the endpoint
        add_headers (dict): additional HTTP headers

    Returns:
        object: requests.response
    """
    if add_headers is None:
        add_headers = {}
    request_url = get_request_url(integration, path)
    # Merge headers
    headers = {**get_headers(), **add_headers}

    response = requests.request(method, request_url, json=payload, headers=headers)
    return response
