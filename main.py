import argparse
from configparser import ConfigParser
from pprint import pprint
from pathlib import Path
from dateutil.parser import parse as date_parse
from datetime import datetime
from operator import itemgetter

from tqdm import tqdm

from cli.stt import WatsonSTT
from cli.visual import VisualSTT
from cli import clean_up

# @TODO: Add the ability to read the url from the conf.ini. Already implemented in visual.py

def main():
    """Entry point of the CLI. 
    
    The program will accept either a "--visual" flag, where it then kicks out to the visual CLI.
    Otherwise, it will accept name, descr, url, oov_file_path, verbose, delete, eval, or audio_file flags.
    Passing certain combination of these flags will trigger different actions such as train, evaluate, or delete.

    Args:
    --visual: kick of the visual CLI. At this point, the control of the program is handed over to the visual.py file
    --url: the url of the instance
    --name: name of the model
    --descr: the description of the model
    --oov_file_path: the filepath of the grammar, vocabulary, or corpus used to train the model

    Returns:
    None
    """
    # setting up the command line
    argparser = argparse.ArgumentParser()

    argparser.add_argument('--visual', help="Run CLI in visual mode. All other flags passed are ignored", action="store_true")
    argparser.add_argument('--name', help="Name of the model")
    argparser.add_argument('--descr', help="A short description of the custom model")
    argparser.add_argument('--url', help="This is the URL of the Watson STT model. \
                                           Found on the start page of the Watson STT tooling.")
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

    visual = args.visual
    name = args.name
    descr = args.descr
    url = args.url
    file_path = args.oov_file_path
    verbose = args.verbose
    delete = args.delete
    evaluate = args.eval
    audio_file = args.audio_file

    if visual:
        VisualSTT().runner()
    
    else:
        if url is None:
            raise Exception("Must pass URL")

    # kick of training
    if name and descr and url and file_path:
        custom_stt = WatsonSTT(url=url)
        custom_stt.create_model(name=name, descr=descr)
        custom_stt.add_corpus(file_path)
        custom_stt.training()
    
    # just add the corpus
    # @TODO: how to create a model and train with an existing corpus?
    # @TODO: is this feature even neccesary? 
    if url and file_path and name is None is file_path is None:
        print("Adding corpus...")
        # @TODO: training a model with an existing uploaded corpus
        custom_stt = WatsonSTT(url=url)
        custom_stt.add_corpus(file_path)
        print("Finished adding corpus")

    # print out the models
    if url and verbose:
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
        clean_up.clean_up(url, delete)
        

'''
    @TODO: what if instead of throwing an error, just provided the date 1/1/1970
    and logged that there was an issue parsing the date. This way the program would still 
    continue
'''
def _to_date(date:str) -> datetime:
    """Convert the date string into date-type.
    
    This helper function is called when displaying models. The function 
    parses the date string and converts it into a date object. 
    The date is used to reverse-chronlogically display the models.
    Throws an exception if it cannot parse the date string.

    Args:
        date: a date string
    
    Returns:
        date: a converted date object

    """

    try:
        return date_parse(date)
    except:
        raise ValueError(f"Error parsing \'{date}\'")


def model_status(url, print=1) -> None:
    """ A wrapper function that returns the status of models.
    This wrapper function is used when the --verbose flag is passed and 
    when the user passes "latest" to train the latest model
    """
    config = ConfigParser()
    config.read('keys/conf.ini')
    api_key = config['API_KEY']['WATSON_STT_API']

    models = WatsonSTT.all_model_status(url=url,
                                        api_key=api_key)

    # flag is set by default to print the results to stdout
    if print:
        pprint(models)

    return models


if __name__ == "__main__":
    main()
