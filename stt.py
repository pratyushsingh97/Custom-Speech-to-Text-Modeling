from configparser import ConfigParser
from pathlib import Path
from string import Template

import requests
import json

import polling

class WatsonSTT(object):
    def __init__(self, url, customization_id=None):
        config = ConfigParser()
        config.read('keys/conf.ini')

        self.API_KEY = config['API_KEY']['WATSON_STT_API']
        self.url = url
        self.customization_id = customization_id
        self.status = None

    def create_model(self, name, descr, model="en-US_BroadbandModel") -> str:
        headers = {'Content-Type': 'application/json',}
        data = {"name": name,
                "base_model_name": model,
                "description": descr}
        data = json.dumps(data)
        
        response = requests.post(f'{self.url}/v1/customizations', 
                                 headers=headers, 
                                 data=data, 
                                 auth=('apikey', self.API_KEY))
        
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

        if self.model_status() == 'pending':
            print("Add a corpus, by calling the add_corpus() function!")
            
            return

        if self.customization_id:
            # check status
            polling.poll(lambda: self.model_status() == 'ready',
                         step=0.1,
                         poll_forever=True)

        print("Training Beginning")

        response = requests.post(f'{self.url}/v1/customizations/{self.customization_id}/train', 
                                 auth=('apikey', self.API_KEY))
        
        
        print("Training...")

        polling.poll(lambda: self.model_status() == 'available',
                     step=0.1,
                     poll_forever=True)
        
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
    
    def transcribe(self, path_to_audio_file, customization_id=None, url=None):
        audio_file = None
        path_to_audio_file = Path(path_to_audio_file)

        if not path_to_audio_file.exists() and not path_to_audio_file.is_file():
            raise FileExistsError("The path of the audio is invalid")
        
        with open(path_to_audio_file, 'rb') as f:
            audio_file = f.read()
        
        # handling the customization id
        if customization_id is None:
            customization_id = self.customization_id
        
        if url is None:
            url = self.url

        # @TODO: check to see if this is a valid audio type
        content_type = path_to_audio_file.suffix.replace('.', '') # parse the audio file type from the stem
        sync_url = f"{url}/v1/recognize?language_customization_id={customization_id}"
        headers = {'Content-Type': f'audio/{content_type}'}
        response = requests.post(url=sync_url, 
                                 data=audio_file, 
                                 headers=headers, 
                                 auth=('apikey', self.API_KEY))

        response = json.loads(response.text)

        return response

    @staticmethod
    def all_model_status(url=None, api_key=None):
        response = requests.get(f'{url}/v1/customizations', auth=('apikey', api_key))

        response = json.loads(response.text)

        return response
    
    @staticmethod
    def delete_model(url=None, api_key=None, customization_id=None):
        try:
            response = requests.delete(f'{url}/v1/customizations/{customization_id}', auth=('apikey', api_key))

            if response.status_code == 200:
                print()
                print(f"Deleting model with id: {customization_id}")

                polling.poll(lambda: WatsonSTT.model_deletion_checker(url, api_key, customization_id),
                            step=0.01,
                            poll_forever=True)
                
                print(f"Model {customization_id} Succesfully Deleted")
                print()
            
            elif response.status_code == 400:
                print()
                print(response.text)
                print()

            elif response.status_code == 401:
                print()
                print(response.text)
                print()
            
            elif response.status_code == 409:
                print()
                print(response.text)
                print()
            
            elif response.status_code == 500:
                print()
                print(response.status_code)
                print()
            
            else:
                print()
                print("An unexpected error occurred")

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

        







