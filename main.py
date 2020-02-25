from stt import WatsonSTT

import argparse
from configparser import ConfigParser
from pprint import pprint


def main():
    # setting up the command line
    argparser = argparse.ArgumentParser()

    argparser.add_argument('--name', help="Name of the model")
    argparser.add_argument('--descr', help="A short description of the custom model")
    argparser.add_argument('--url', help="This is the URL of the Watson STT model. Found on the start page of the Watson STT tooling.")
    argparser.add_argument('--oov_file_path', help="The path of the out-of-vocabulary file (the corpus, words, or grammar)")
    argparser.add_argument('-v', '--verbose', '--list_models',  help="Shows you all of the models trained on this account", action="store_true")
    argparser.add_argument('--delete', help="Pass the customization id of the models to delete", action="store_true")

    args = argparser.parse_args()

    name = args.name
    descr = args.descr
    url = args.url
    file_path = args.oov_file_path
    verbose = args.verbose
    delete = args.delete


    if name and descr and url and file_path:
        custom_stt = WatsonSTT(url=url)
        customization_id = custom_stt.create_model(name=name,
                                                descr=descr)
        custom_stt.add_corpus(file_path)
        custom_stt.training()

    if url and verbose:
        model_status(url)
    
    if url and delete:
        clean_up(url, delete)


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

    for ids in customization_ids:
        WatsonSTT.delete_model(url, api_key, customization_id=ids)

if __name__ == "__main__":
    main()