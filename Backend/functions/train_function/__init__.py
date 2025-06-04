import azure.functions as func
import logging
import pandas as pd
from io import BytesIO
from shared.preprocessing_utils import preprocess
from shared.model_utils import train_and_save_model
from datetime import datetime, timezone

def main(inputblob: func.InputStream, 
         modeloutput: func.Out[bytes],
         scaleroutput: func.Out[bytes],
         cleanedoutput: func.Out[bytes],
         name: str):
    logging.info(f"Function triggered for blob: {inputblob.name}")
    
    try:
        # Determina il tipo di vino
        filename = name.lower().strip()
        if "red" in filename:
            wine_type = "red"
        elif "white" in filename:
            wine_type = "white"
        else:
            logging.warning("Wine type not recognized")
            return
        
        logging.info(f"Wine type detected: {wine_type}")
        
        # Carica e preprocessa i dati
        df_raw = pd.read_csv(BytesIO(inputblob), sep=";")
        df_cleaned, scaler = preprocess(df_raw)
        
        # Salva i dati preprocessati
        cleanedoutput.set(df_cleaned.to_csv(index=False).encode())
        
        # Training e salvataggio del modello
        model_bytes, scaler_bytes = train_and_save_model(df_cleaned, scaler)
        
        # Salva modello e scaler
        modeloutput.set(model_bytes)
        scaleroutput.set(scaler_bytes)
        
        logging.info("Training and save completed successfully")
        
    except Exception as e:
        logging.error(f"Error in training function: {str(e)}")
        logging.exception("Full stack trace:")
        raise