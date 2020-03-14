
from tqdm import tqdm
from configparser import ConfigParser

from cli.stt import WatsonSTT

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