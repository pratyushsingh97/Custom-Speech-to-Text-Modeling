from __future__ import print_function, unicode_literals
from pprint import pprint
from configparser import ConfigParser
from pathlib import Path
from operator import itemgetter

from PyInquirer import prompt, print_json
from examples import custom_style_2
from tqdm import tqdm

from cli.stt import WatsonSTT

class VisualSTT(object):
    def __init__(self):
        self.url = None
        self.api_key = None

    def account_details(self):
        account_details = [{
            "type": "input",
            "message": "Enter the URL for your Watson Speech-to-Text Model. Visit cloud.ibm.com to find this information.",
            "name": "watson_stt_url",
            "default": "None"
        },
        {
            "type": "password",
            "message": "Enter your API Key for your Watson Speech-to-Text Model. Visit cloud.ibm.com to find this information.",
            "name": "watson_stt_api_key",
            "default": "None"
        }]

        return account_details


    def main_questions(self):
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
    

    def train_questions(self):
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
    
    def evaluate_questions(self):
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
        path = Path('./keys/conf.ini').resolve()

        config = ConfigParser()
        config.read(path)
        config['URL'] = {"WATSON_STT_URL": url}

        with open(path, 'w') as configfile:
            config.write(configfile)
    
    def _save_api_key(self, api_key=None) -> None:
        path = Path('./keys/conf.ini').resolve()

        config = ConfigParser()
        config.read(path)
        config['API_KEY'] = {"WATSON_STT_API": api_key}
        
        with open(path, 'w') as configfile:
            config.write(configfile)
    
    def _model_keys(self):
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
        delete = [{
            "type": "input",
            "name": "delete_all",
            "message": "Do you want to delete all models? (y/N)"
        }]

        return delete
    
    def _delete_specific_models(self) -> tuple:
        # all_models = WatsonSTT.all_model_status(url=self.url, api_key=self.api_key)
        # all_models = all_models['customizations']
        # lst_models_delete = []
        # models_to_id = {}

        # for model in all_models:
        #     key = f"{model['name']} -- {model['description']} -- Created at: {model['created']}"
        #     lst_models_delete.append({"name": key})
        #     models_to_id[key] = model['customization_id']

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
                print("Attempting to read in api key from configuration file")
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

                stt = WatsonSTT(url=self.url)
                stt.create_model(name=model_name, descr=model_descr)
                stt.add_corpus(oov_file_path)
                stt.training()

            if 'Evaluate' in model_options:
                model_id, evaluate_answers = self.evaluate_questions()
                evaluate_models = prompt(evaluate_answers, style=custom_style_2)
                
                path_to_audio_file = evaluate_models['audio_file']
                evaluate_models = evaluate_models['models_evaluate']

                custom_ids = [model_id[eval_model] for eval_model in evaluate_models]

                for index, id in enumerate(custom_ids):
                    stt = WatsonSTT(url=self.url, customization_id=id)
                    results = stt.transcribe(path_to_audio_file)

                    print()
                    print("*" * 60)
                    print(f"Transcription Results from {evaluate_models[index]}:")
                    pprint(results)
                    print()
                    print("*" * 60)
                    print()

            
            if 'See Available Models' in model_options:
                models = WatsonSTT.all_model_status(url=self.url, api_key=self.api_key)
                pprint(models)

            if 'Delete' in model_options:
                delete_options = prompt(self.delete(), style=custom_style_2) 
                delete_options = delete_options['delete_all'].strip().lower()
                
                if delete_options in ('y', 'yes'):
                    VisualSTT.clean_up(url=self.url, customization_ids=['all'])
                elif delete_options in ('n', 'no'):
                    models_id, models_delete = self._delete_specific_models()
                    selected_models = prompt(models_delete, style=custom_style_2)
                    
                    models_to_delete = selected_models['models_to_delete']
                    custom_ids_del_models = [models_id[del_model] for del_model in models_to_delete]

                    # delete the models 
                    VisualSTT.clean_up(self.url, custom_ids_del_models)
        
        except KeyboardInterrupt:
            print("Action Cancelled")
                

    # @TODO: find a better place to put this function
    @staticmethod
    def clean_up(url, customization_ids):
        config = ConfigParser()
        config.read('keys/conf.ini')
        api_key = config['API_KEY']['WATSON_STT_API']

        if customization_ids[0] == 'all':
            confirmation = input('Are you sure you want to delete all of the trained models? (y/N): ')
            confirmation = confirmation.strip().lower()
            if confirmation in ('y', 'yes'):
                models = WatsonSTT.all_model_status(url=url, api_key=api_key)
                if 'customizations' in models.keys():
                    models = models['customizations']
                    for model in tqdm(models, desc="Deleting All Models", leave=False):
                        _id = model['customization_id']
                        WatsonSTT.delete_model(url, api_key, _id)
                else:
                    print("No models to delete.")
            
            elif confirmation in ('n', 'no'):
                print("No models were deleted. Action cancelled.")
            else:
                print("Could not understand response.")

            return 

        else:
            for ids in tqdm(customization_ids, desc="Deleting Customization Models", leave=False):
                result = WatsonSTT.delete_model(url, api_key, customization_id=ids)

                if not result:
                    return

if __name__ == "__main__":
    VisualSTT().runner()
