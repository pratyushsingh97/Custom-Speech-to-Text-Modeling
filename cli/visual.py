from __future__ import print_function, unicode_literals
from pprint import pprint
from configparser import ConfigParser
from pathlib import Path
from operator import itemgetter

from PyInquirer import prompt, print_json
from examples import custom_style_2
from tqdm import tqdm

from cli.stt import WatsonSTT
from cli import clean_up

# make sure the front end can handle the error thrown by the backend - just print error
# @TODO: What happens if training fails? (check)
# @TODO: What happens if adding a corpus fails? (check)
# @TODO: What happens if creating a model fails? (check)
# @TODO: What if deleting a model fails?
# @TODO: What happens if evaluate fails (check)
# @TODO: add code to grab the exceptions from the backend to the front
# @TODO: authentication failures?

class VisualSTT(object):
    """The VisualSTT class is the front-end of the visual component of the CLI.
    The Visual CLI provides an interactive GUI to form your pipeline of actions./

    Attributes:
    url: url of the instance
    apikey: the API key associated with that instance 
    """

    def __init__(self):
        self.url = None
        self.api_key = None

    def account_details(self) -> list:
        """ The initial launch screen that asks for your url and apikey.
        
        The URL and API KEY are stored in the conf.ini file. If there is a key
        already available, then it prefills the menu.

        Args: None
        Returns: a formatted list dictionaries so Py-Inquirer can present them to the user
        """

        path = Path('./keys/conf.ini').resolve()
        config = ConfigParser()
        config.read(path)
        
        default_url = ""
        default_apikey = ""
        if 'URL' in config.sections() and 'API_KEY' in config.sections():
            default_url = config['URL']['watson_stt_url']
            default_apikey = config['API_KEY']['WATSON_STT_API']

        account_details = [{
            "type": "input",
            "message": "Enter the URL for your Watson Speech-to-Text Model. Visit cloud.ibm.com to find this information.",
            "name": "watson_stt_url",
            "default": default_url
        },
        {
            "type": "password",
            "message": "Enter your API Key for your Watson Speech-to-Text Model. Visit cloud.ibm.com to find this information.",
            "name": "watson_stt_api_key",
            "default": default_apikey
        }]

        return account_details


    def main_questions(self) -> list:
        """ The user is asked to choose one or more options between 
        Train, Eval, See Available Models, and Delete

        Args:
            None
        
        Returns:
            main: list of options to take
        
        """

        main = [{
            'type': 'checkbox',
            'qmark': '🗣 ',
            'message': 'Select One or More Actions to Take on Speech-to-Text Models',
            'name': 'custom_models_options',
            'choices': [
                {
                    'name': 'Train'
                },
                {
                    'name': 'Evaluate'
                },
                {   
                    'name': 'See Available Models'
                },
                {
                    'name': "Delete"
                }

            ],
            'validate': lambda answer: 'You must choose at least one option.' \
                if len(answer) == 0 else True
        }]

        return main
    

    def train_questions(self) -> list:
        """ Asks the user to provide a name, description, and file path 
        of the training data

        Args:
            None
        
        Returns:
            train: list of questions that ask the name, a description of the model, and file path of the training data
        """
        train = [{
            "type": 'input',
            "message": "Provide a name for your model: ",
            "name": "model_name"
        },
        {
            "type": 'input',
            "message": "Provide a brief description for your model: ",
            "name": "model_description",
        },
        {
            "type": 'input',
            "message": "Provide the file path for custom model training data.",
            "name": "oov_file_path"
        }]

        return train
    
    def evaluate_questions(self) -> tuple:
        """ Presents a list of models to transcribe the audio file
        The options presented are hashed with the customization id as the value. 
        When the model option is chosen the customization id is passed to transcribe the model.

        Args: None 
        Returns: 
           evaluate: an array to pyinquirer to present the user 
        with the models and a question to ask the file path of the audio file
            model_id: a dictionary with the model name as the key and the customization as the key
        """

        models_to_id, evaluate_models = self._model_keys()

        evaluate = [{
            "type": 'input',
            "message": "Provide a file path for the audio file",
            "name": "audio_file"
        },
        {
            "type": "checkbox",
            "qmark": '📝',
            "message": 'Select one or more models to evaluate',
            "name": "models_evaluate",
            "choices": evaluate_models
        }
        ]

        return models_to_id, evaluate
    
    def _save_url(self, url=None) -> None:
        """ Helper function that saves the url to the config file

        Args:
            url: url of the instance
        Returns:
            None
        """

        path = Path('./keys/conf.ini').resolve()

        config = ConfigParser()
        config.read(path)
        config['URL'] = {"WATSON_STT_URL": url}

        with open(path, 'w') as configfile:
            config.write(configfile)
    
    def _save_api_key(self, api_key=None) -> None:
        """ Helper function that saves the API to the config file

        Args:
            url: API Key of the instance
        Returns:
            None
        """

        path = Path('./keys/conf.ini').resolve()

        config = ConfigParser()
        config.read(path)
        config['API_KEY'] = {"WATSON_STT_API": api_key}
        
        with open(path, 'w') as configfile:
            config.write(configfile)
    
    def _model_keys(self) -> tuple:
        """ Maps the model name and created date along with the description as the key 
        and the customization id as the value.

        Args:
        None

        Returns:
        models_to_id: the dictionary that maps the model name, 
        created time, and description as the key and the customization id as the key
        
        model_name: name of the models to present to user
        """

        all_models = WatsonSTT.all_model_status(url=self.url, api_key=self.api_key)
        all_models = all_models['customizations']
        all_models = sorted(all_models, key=itemgetter('created'), reverse=True) # sort models by date
        
        model_name = []
        models_to_id = {}

        for model in all_models:
            key = f"{model['name']} -- {model['description']} -- Created at: {model['created']}"
            model_name.append({"name": key})
            models_to_id[key] = model['customization_id']
        
        return models_to_id, model_name
    
    def delete(self) -> list:
        """User can choose to delete all models or specific models

        Args
        None

        Returns
        delete: questions to ask the user on delete options
        """
        delete = [{
            "type": "input",
            "name": "delete_all",
            "message": "Do you want to delete all models? (y/N)"
        }]

        return delete
    
    def _delete_specific_models(self) -> tuple:
        """ If the user selects to delete only specific models, 
        then present the user with specific models to delete

         The options presented are hashed with the customization id as the value. 
         When an option is chosen, the customization id is processed to delete the 
         model 

        Args:
        None

        Returns:

        """

        models_to_id, models_to_delete = self._model_keys() 

        # implement hash function to store the "name" as the key and the customization id as the value
        model_choices = [{
            'type': 'checkbox',
            'qmark': '❌',
            'message': 'Choose one or more models to delete',
            'name': 'models_to_delete',
            'choices': models_to_delete
        }]

        return models_to_id, model_choices
    
    def runner(self):
        """ The runner parses the options selected and then calls 
        the backend functions from WatsonSTT class
        """
        try:
            account_details = prompt(self.account_details(), style=custom_style_2)
            
            if account_details['watson_stt_url'] is "None":
                print()
                print("Attempting to read in url from configuration file")
                try:
                    path = Path('./keys/conf.ini').resolve()
                    config = ConfigParser()
                    config.read(path)
                    self.url = config['URL']['WATSON_STT_URL']

                    print("Succesfully read URL.")
                    print()
                
                except:
                    print("Uh oh! We failed to read the URL from the configuration file.")
                    raise ValueError("Failure to read URL from conf.ini file")
            
            else:
                url = account_details['watson_stt_url']
                self.url = url
                self._save_url(self.url)

            if account_details['watson_stt_api_key'] is "None":
                print("Attempting to read in API key from configuration file")
                try:
                    path = Path('./keys/conf.ini').resolve()
                    config = ConfigParser()
                    config.read(path)
                    self.api_key = config['API_KEY']['WATSON_STT_API']

                    print("Succesfully read in API key.")
                    print()
                
                except:
                    print("Uh oh! We failed to read the API Key from the configuration file.")
                    raise ValueError("Failure to read API key from conf.ini file")

            else:
                api_key = account_details['watson_stt_api_key']
                self.api_key = api_key
                self._save_api_key(api_key)

            answers = prompt(self.main_questions(), style=custom_style_2)
            model_options  = answers['custom_models_options']

            if 'Train' in model_options:
                # ask train questions
                train = prompt(self.train_questions(), style=custom_style_2)

                model_name = train['model_name']
                model_descr = train['model_description']
                oov_file_path = train['oov_file_path']

                try:
                    stt = WatsonSTT(url=self.url)
                    stt.create_model(name=model_name, descr=model_descr)
                    stt.add_corpus(oov_file_path)
                    stt.training()
                except Exception as e:
                    print(e)

            if 'Evaluate' in model_options:
                model_id, evaluate_answers = self.evaluate_questions()
                evaluate_models = prompt(evaluate_answers, style=custom_style_2)
                
                path_to_audio_file = evaluate_models['audio_file']
                evaluate_models = evaluate_models['models_evaluate']

                custom_ids = [model_id[eval_model] for eval_model in evaluate_models]

                for index, id in enumerate(custom_ids):
                    stt = WatsonSTT(url=self.url, customization_id=id)
                    try:
                        results = stt.transcribe(path_to_audio_file)

                        print()
                        print("*" * 60)
                        print(f"Transcription Results from {evaluate_models[index]}:")
                        pprint(results)
                        print()
                        print("*" * 60)
                        print()
                    
                    except Exception as e:
                        print("*" * 60)
                        print()
                        print(f"Transcribing model {evaluate_models[index]} failed.")
                        print(e)
                        print("*" * 60)
                        print()

            
            if 'See Available Models' in model_options:
                models = WatsonSTT.all_model_status(url=self.url, api_key=self.api_key)
                pprint(models)

            # check if the model can be deleted
            # error of the model should be 409
            if 'Delete' in model_options:
                delete_options = prompt(self.delete(), style=custom_style_2) 
                delete_options = delete_options['delete_all'].strip().lower()
                
                if delete_options in ('y', 'yes'):
                    clean_up.clean_up(url=self.url, customization_ids=['all'])
                elif delete_options in ('n', 'no'):
                    models_id, models_delete = self._delete_specific_models()
                    selected_models = prompt(models_delete, style=custom_style_2)
                    
                    models_to_delete = selected_models['models_to_delete']
                    custom_ids_del_models = [models_id[del_model] for del_model in models_to_delete]

                    # delete the models 
                    clean_up.clean_up(self.url, custom_ids_del_models)
                else:
                    print("Only \'yes\' and \'no\' inputs allowed")
                    raise KeyboardInterrupt
        
        except KeyboardInterrupt:
            print("Action Cancelled")

if __name__ == "__main__":
    VisualSTT().runner()
