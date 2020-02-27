import argparse
from configparser import ConfigParser
from pprint import pprint

from tqdm import tqdm

from stt import WatsonSTT

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

    if url and file_path:
        # @TODO: training a model with an existing uploaded corpus
        custom_stt = WatsonSTT(url=url)
        custom_stt.add_corpus(file_path)

    if url and verbose:
        model_status(url)
    
    if url and delete:
        clean_up(url, delete)
    
    if url and evaluate and audio_file:
        custom_stt = WatsonSTT(url=url)
        # @TODO: build this out
        if evaluate == 'latest':
            pass

        print("Transcribing the audio file...")
        results = custom_stt.transcribe(audio_file, url=url, customization_id=evaluate)
        print("Transcribing finished")
        print()
        print()
        pprint(results)
        


def model_status(url):
    config = ConfigParser()
    config.read('keys/conf.ini')
    api_key = config['API_KEY']['WATSON_STT_API']

    models = WatsonSTT.all_model_status(url=url,
                                        api_key=api_key)

    pprint(models)

def clean_up(url, customization_ids):
    config = ConfigParser()
    config.read('keys/conf.ini')
    api_key = config['API_KEY']['WATSON_STT_API']

    if customization_ids == 'all':
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

            return 

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
