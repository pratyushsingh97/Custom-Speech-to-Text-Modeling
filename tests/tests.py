import os
import argparse
import pytest
import requests
import json
import unittest

from unittest.mock import Mock, patch

from cli.stt import WatsonSTT


url = "https://api.us-south.speech-to-text.watson.cloud.ibm.com/instances/019c8853-fd9f-47c3-8e1d-0a701e931beb"

@pytest.fixture(params=[201, 400, 401, 500])
def error_codes(request):
    print(request)
    return request.params

@patch('cli.stt.requests.post')
def test_create_model(mock):
    if error_codes == 201:
        mock.return_value.status_code = 201

        expected_response = json.dumps({'customization_id': '1234'})
        mock.return_value.text = expected_response

        response = WatsonSTT(url=url).create_model(name="Testing Model",
                                                   descr="From test")

        assert response == 1234
    
    elif error_codes == 400:
        mock.return_value.status_code = 400
        # expected_response = 


