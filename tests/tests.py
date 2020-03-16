import os
import argparse
import pytest
import requests
import json
import unittest

from configparser import ConfigParser
from unittest.mock import Mock, patch
from pathlib import Path, PosixPath
from random import random

from cli.stt import WatsonSTT

# dummpy class to test invalid types
class InvalidType(object):
    def __init__(self, dummy_input=""):
        self.dummy_value = dummy_input

path = Path('./keys/conf.ini')
config = ConfigParser()
config.read(path)
url = config['URL']["watson_stt_url"]

@pytest.fixture(params=[201, 400, 401, 500])
def error_codes(request):
    return request.param

@patch('cli.stt.requests.post')
def test_create_model(mock, error_codes):
    if error_codes == 201:
        mock.return_value.status_code = 201

        expected_response = json.dumps({'customization_id': '1234'})
        mock.return_value.text = expected_response

        response = WatsonSTT(url=url).create_model(name="Testing Model",
                                                   descr="From test")

        assert response == '1234'
        
        # testing if the API messes up does not have a 'customization_id'
        missing_response = json.dumps({'blah': 'blah'})
        mock.return_value.text = missing_response

        with pytest.raises(Exception, match="The Watson STT request failed. Please try again."):
            WatsonSTT(url).create_model(name="Testing", descr="from test")

def test_invalid_create_model_params():
    with pytest.raises(TypeError, match=r".* 'name' .*"):
       WatsonSTT(url).create_model(name=InvalidType(), descr="valid")
    
    with pytest.raises(TypeError, match=r".* 'descr' .*"):
       WatsonSTT(url).create_model(name="valid", descr=InvalidType())

def test_training_no_customization_id():
    with pytest.raises(ValueError, match="No customization id is provided!"):
        WatsonSTT(url).training()

@patch('cli.stt.Path')
def test_adding_corpus(mock):
    mock.return_value = PosixPath('blah')
    mock.exists().return_value = False
    with pytest.raises(FileExistsError, match="The path of the file is invalid"):
        WatsonSTT(url=url).add_corpus("blah")

@patch('cli.stt.Path')
def testing_adding_corpus2(mock):
    mock.return_value = PosixPath('blah')
    mock.exists().return_value = True
    mock.is_file().return_value = False
    with pytest.raises(FileExistsError, match="The path of the file is invalid"):
        WatsonSTT(url=url).add_corpus("blah")

    






    




