from configparser import ConfigParser
from pathlib import Path
from string import Template
from time import sleep

import requests
import json

import polling
from progress.spinner import PixelSpinner

class WatsonSTT(object):
    """ The WatsonSTT class is the backend of the CLI. This class is the wrapper class around
    the IBM Watson STT API. 

    Attributes:
        API_KEY: reads from the conf.ini file and stores the API as a class variable
        name: name of the model
        descr: description of the model
        model_type: name of the baseband of the model (i.e. english broadband)
        url: url of the instance
        customization_id: customization id of the model
        status: the STT API provides several states for the model. This variable keeps track of the state
    """

    def __init__(self, url, customization_id=None):
        """ Inits the class variables.
        Args: 
        url: url of the STT instance
        customization_id: id of the STT instance.
        """

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
        """Creates a model with the name, descr parameters, and it is trained on the model parameter.

        Args:
            name: name of the model
            descr: description of the model
            model: the type of STT model.
        
        Returns:
            customization_id: a unique identifier for the model

        """

        if type(name) != str:
            raise TypeError("The \'name\' of the model must be a \'str\'")
        
        if type(descr) != str:
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

            if 'customization_id' not in response.keys():
                raise Exception("The Watson STT request failed. Please try again.")

            self.customization_id = response['customization_id']
            self.status = 'pending' # this is the initial status of the model

            print("Model created with id: ", self.customization_id)

            return response['customization_id']

        else:
            raise Exception(response.text)
    
    def training(self):
        """Kicks off the training suite. 

        To begin training, the model needs to be in the 'ready' state. Training continues
        until the model reaches the 'available' state. 

        Args:
            -None
        
        Returns:
            - a completion of the training acknowledgement
        """

        if self.customization_id is None:
            raise ValueError("No customization id provided!")

        if self.customization_id:
            # check status
            with PixelSpinner("Allocating resources to begin training ") as bar:
                while self.model_status() != 'ready':
                    sleep(0.1)
                    bar.next()

        response = requests.post(f'{self.url}/v1/customizations/{self.customization_id}/train', 
                                 auth=('apikey', self.API_KEY))
        
        if response.status_code == 200:
            print("Training Beginning")
        
            with PixelSpinner(f"Training {self.name} ") as bar:
                while self.model_status() != 'available':
                    sleep(0.1)
                    bar.next()
            
            print("Training has finished")
            response = json.loads(response.text)

            return response
        
        else:
            raise Exception(response.text)
        
    def add_corpus(self, corpus_path: str) -> None:
        """ Adds corpus/grammar/oov to a model. A customization id is required.

        Args:
            corpus_path: the path to the corpus 
        Returns:
            None
        
        """

        if type(corpus_path) != str:
            raise TypeError("The path must be a string")

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
        """ A function that returns the state of the model

        Args: None
        Returns:
            status: a string describing the status
        """

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
        """Takes in a path to the audio file to transcribe
        and returns the trancription of the audio along with the confidence levels

        Args:
        path_to_audio_file: string to the audio file

        Returns
        response: a json object of the transcription that also contains metadata on the confidence
        of the transcription
        """

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
    def all_model_status(url=None, api_key=None) -> list:
        """A helper function that returns the states for ALL models created
        
        Args:
        url: instance url
        api_key

        Returns
        - a json array of the models created on the instance and their url along with all other metadata
        """

        response = requests.get(f'{url}/v1/customizations', auth=('apikey', api_key))
        response = json.loads(response.text)

        return response
    
    @staticmethod
    def delete_model(url:str=None, api_key:str=None, customization_id:str=None) -> bool:
        """ Deletes the models with the passed configuration ids.

        The function accepts the url and apikey of the instance along with the customization id
        of the model that needs to be deleted.

        Args:
        url
        api_key
        customization_id: a unique identifier for a custom stt model

        Returns
        a boolean to siginify whether deleting the model was succcessful
        """ 

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
            
            else:
                raise Exception(response.text)

        except Exception as e:
                print(e)
    
    @staticmethod
    def model_deletion_checker(url, api_key, customization_id):
        """ Helper function that pings the API to confirm if the API was deleted

        Args:
        url
        api_key
        customization_id: a unique identifier for a custom stt model

        Returns
        a boolean to siginify whether deleting the model was succcessful

        """

        response = requests.get(f'{url}/v1/customizations/{customization_id}', 
                                auth=('apikey', api_key))

        if response.status_code in [200, 401]:
            return True
        
        if response.status_code in [400, 500]:
            raise Exception(response.text)

        







