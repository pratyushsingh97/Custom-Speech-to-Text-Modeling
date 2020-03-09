import argparse
from configparser import ConfigParser
from pprint import pprint
from pathlib import Path
from dateutil.parser import parse as date_parse
from datetime import datetime
from operator import itemgetter

from tqdm import tqdm

from cli.stt import WatsonSTT
from visual import VisualSTT

# @TODO: Add the ability to read the url from the conf.ini. Already implemented in visual.py
# @TODO: Add a visual flag to kickstart the process in visual mode. Should be the first thing the program checks for 

def main():
    # setting up the command line
    argparser = argparse.ArgumentParser()

    argparser.add_argument('--name', help="Name of the model")
    argparser.add_argument('--descr', help="A short description of the custom model")
    argparser.add_argument('--url', help="This is the URL of the Watson STT model. \
                                           Found on the start page of the Watson STT tooling.", required=True)
    argparser.add_argument('--oov_file_path', help="The path of the out-of-vocabulary \
                                                    file (the corpus, words, or grammar)")
    argparser.add_argument('-v', '--verbose', '--list_models', help="Shows you all \
                                                                     of the models trained on this account", \
                                                                action="store_true")
    argparser.add_argument('--delete', nargs='+', help="Pass the customization id of the models to delete")
    argparser.add_argument('--eval', help="Evaluate the trained model against an audio-file. \
                                           \nPass in the \'customization_id\' of the model or \
                                            pass \'latest\' to train the latest trained model. \
                                            \nThe \'audio_file\' flag must be set as well!")
    argparser.add_argument('--audio_file', help="The path of the audio file to transcribe.")

    args = argparser.parse_args()

    name = args.name
    descr = args.descr
    url = args.url
    file_path = args.oov_file_path
    verbose = args.verbose
    delete = args.delete
    evaluate = args.eval
    audio_file = args.audio_file

    if name and descr and url and file_path:
        custom_stt = WatsonSTT(url=url)
        custom_stt.create_model(name=name, descr=descr)
        custom_stt.add_corpus(file_path)
        custom_stt.training()

    if url and file_path and name is None is file_path is None:
        print("Adding corpus...")
        # @TODO: training a model with an existing uploaded corpus
        custom_stt = WatsonSTT(url=url)
        custom_stt.add_corpus(file_path)
        print("Finished adding corpus")

    if verbose:
        print("Retrieving Models...")
        model_status(url)
    
    if url and evaluate and audio_file:
        # pass in customization id 
        print("Checking audio file...")
        path = Path(audio_file)
        if not path.exists() and not path.is_file():
            raise FileExistsError("Cannot find audio file")

        if evaluate == "latest":
            models = model_status(url, print=0)
            models = models['customizations']

            if len(models) == 0:
                print("You do not have any trained models. Please create and train a model before evaluating.")
                return 

            # convert the date string into date object
            for model in models:
                model['created'] = _to_date(model['created'])

            models = sorted(models, key=itemgetter('created'), reverse=True)
            evaluate = models[0]['customization_id']

        print("Transcribing the audio file...")
        custom_stt = WatsonSTT(url=url, customization_id=evaluate)
        results = custom_stt.transcribe(audio_file)
        print("Transcribing finished")
        print()
        pprint(results)

    if url and delete:
        clean_up(url, delete)
        

def _to_date(date:str) -> datetime:
    try:
        return date_parse(date)
    except:
        raise ValueError(f"Error parsing \'{date}\'")


def model_status(url, print=1) -> None:
    config = ConfigParser()
    config.read('keys/conf.ini')
    api_key = config['API_KEY']['WATSON_STT_API']

    models = WatsonSTT.all_model_status(url=url,
                                        api_key=api_key)

    # flag is set by default to print the results to stdout
    if print:
        pprint(models)

    return models


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
    main()
