import os
import argparse
import pytest
import requests
import json
import unittest

from unittest.mock import Mock, patch

from cli.stt import WatsonSTT


class Testing(unittest.TestCase):
    def __init__(self):
        self.url = "https://api.us-south.speech-to-text.watson.cloud.ibm.com/instances/019c8853-fd9f-47c3-8e1d-0a701e931beb"
    
    @patch('cli.stt.requests.post')
    def test_create_model(self, mock):
            mock.return_value.status_code = 201

            expected_response = json.dumps({'customization_id': '1234'})
            mock.return_value.text = expected_response
            
            response = WatsonSTT(url=self.url).create_model(name="Testing Model",
                                                        descr="From test")

            self.assertEqual(response, '1234')
    

