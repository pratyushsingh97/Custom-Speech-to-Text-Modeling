from configparser import ConfigParser
from pathlib import Path
from string import Template
from time import sleep

import requests
import json

import polling
from progress.spinner import PixelSpinner

class WatsonSTT(object):
    def __init__(self, url, customization_id=None):
        config = ConfigParser()
        config.read('keys/conf.ini')

        self.API_KEY = config['API_KEY']['WATSON_STT_API']

        self.name = ""
        self.descr = ""
        self.model_type = ""

        self.url = url
        self.customization_id = customization_id
        self.status = None

    def create_model(self, name: str, descr:str, model="en-US_BroadbandModel") -> str:
        if type(name) != str:
            raise TypeError("The \'name\' of the model must be a \'str\'")
        
        if type(name) != str:
            raise TypeError("The \'descr\' of the model must be a \'str\'")

        headers = {'Content-Type': 'application/json',}
        data = {"name": name,
                "base_model_name": model,
                "description": descr}
        data = json.dumps(data)
        
        response = requests.post(f'{self.url}/v1/customizations', 
                                 headers=headers, 
                                 data=data, 
                                 auth=('apikey', self.API_KEY))
        
        self.name = name
        self.descr = descr
        self.model_type = model
        
        if response.status_code == 201:
            response = json.loads(response.text)

            self.customization_id = response['customization_id']
            self.status = 'pending' # this is the initial status of the model

            print("Model created with id: ", self.customization_id)

            return response['customization_id']
        
        if response.status_code == 400:
            raise ValueError(response.text)

        if response.status_code == 401:
            raise ValueError("The credentials are invalid")
        
        if response.status_code == 500:
            raise ValueError("Internal Server Error")
    
    def training(self):
        if self.customization_id is None:
            raise ValueError("No customization id provided!")

        if self.customization_id:
            # check status
            with PixelSpinner("Allocating resources to begin training ") as bar:
                while self.model_status() != 'ready':
                    sleep(0.1)
                    bar.next()

        print("Training Beginning")
        response = requests.post(f'{self.url}/v1/customizations/{self.customization_id}/train', 
                                 auth=('apikey', self.API_KEY))
        
        
        with PixelSpinner(f"Training {self.name} ") as bar:
            while self.model_status() != 'available':
                sleep(0.1)
                bar.next()
        
        print("Training has finished")
        response = json.loads(response.text)

        return response
        
    def add_corpus(self, corpus_path: str) -> None:
        # check if file exists 
        corpus_name = None

        path = Path(corpus_path)
        if not path.exists() and not path.is_file():
            raise FileExistsError("The path of the file is invalid")

        data = open(str(path), 'rb').read()
        corpus_name = path.stem

        url = f'{self.url}/v1/customizations/{self.customization_id}/corpora/{corpus_name}'
        response = requests.post(url, data=data, auth=('apikey', self.API_KEY))

        if response.status_code == 201:
            print("Corpus Successfully Added")
    
    def model_status(self):
        response = requests.get(f'{self.url}/v1/customizations/{self.customization_id}', 
                                auth=('apikey', self.API_KEY))
        

        if self.customization_id is None:
            raise ValueError("Create a custom model first by calling the create_model method.")

        if response.status_code == 200:
            response = json.loads(response.text)

            return response['status']

        else:
            raise Exception(response.text)
    
    def transcribe(self, path_to_audio_file):
        audio_file = None
        path_to_audio_file = Path(path_to_audio_file)

        if not path_to_audio_file.exists() and not path_to_audio_file.is_file():
            raise FileExistsError("The path of the audio is invalid")
        
        with open(path_to_audio_file, 'rb') as f:
            audio_file = f.read()
        
        # @TODO: check to see if this is a valid audio type
        content_type = path_to_audio_file.suffix.replace('.', '') # parse the audio file type from the stem
        sync_url = f"{self.url}/v1/recognize?language_customization_id={self.customization_id}"
        headers = {'Content-Type': f'audio/{content_type}'}
        response = requests.post(url=sync_url, 
                                 data=audio_file, 
                                 headers=headers, 
                                 auth=('apikey', self.API_KEY))
        

        if response.status_code == 200:
            response = json.loads(response.text)
            
            return response

        else:
            raise Exception(response.text)

        

    @staticmethod
    def all_model_status(url=None, api_key=None):
        response = requests.get(f'{url}/v1/customizations', auth=('apikey', api_key))

        response = json.loads(response.text)

        return response
    
    @staticmethod
    def delete_model(url=None, api_key=None, customization_id=None) -> bool:
        try:
            response = requests.delete(f'{url}/v1/customizations/{customization_id}', auth=('apikey', api_key))

            if response.status_code == 200:
                print()

                with PixelSpinner(f"Deleting model with id: {customization_id} ") as bar:
                    while not WatsonSTT.model_deletion_checker(url, api_key, customization_id):
                        sleep(0.01)
                        bar.update()
                
                print(f"Model {customization_id} Succesfully Deleted")
                print()

                return True
            
            elif response.status_code == 400:
                print("Bad request. The specified customization ID is invalid")
                print()

            elif response.status_code == 401:
                print(response.text)
                print()

            elif response.status_code == 409:
                print(response.text)
                print()        
            
            elif response.status_code == 500:
                print(response.text)
                print()
            
            else:
                print("An unexpected error occurred")
            

            return False

        except Exception as e:
                print(e)
    
    @staticmethod
    def model_deletion_checker(url, api_key, customization_id):
        response = requests.get(f'{url}/v1/customizations/{customization_id}', 
                                auth=('apikey', api_key))


        if response.status_code in [200, 401]:
            return True
        
        if response.status_code in [400, 500]:
            raise Exception(response.text)

        







