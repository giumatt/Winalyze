import azure.functions as func
import logging
from azure.storage.blob import BlobServiceClient 
from shared.model_utils import load_model
import pandas as pd
import json
import os

def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Richiesta di inferenza ricevuta')
    
    try:
        # Ottieni e valida i dati di input
        try:
            data = req.get_json()
            wine_type = data.pop("type", "").lower()
        except ValueError:
            return func.HttpResponse(
                "Invalid JSON in request body",
                status_code=400
            )

        # Valida il tipo di vino
        if wine_type not in ['red', 'white']:
            return func.HttpResponse(
                "Please specify 'type' as 'red' or 'white'",
                status_code=400
            )
        
        logging.info(f'Richiesta predizione per vino {wine_type}')
        
        # Carica il modello
        try:
            model, scaler = load_model(wine_type)
            logging.info('Modello caricato con successo')
        except Exception as e:
            logging.error(f'Errore nel caricamento del modello: {str(e)}')
            return func.HttpResponse(
                f"Model loading error: {str(e)}",
                status_code=500
            )

        # Prepara i dati e fai la predizione
        try:
            df = pd.DataFrame([data])
            X_scaled = scaler.transform(df)
            prediction = model.predict(X_scaled)
            logging.info('Predizione completata con successo')
            
            return func.HttpResponse(
                json.dumps({"prediction": int(prediction[0])}),
                mimetype="application/json"
            )
        except Exception as e:
            logging.error(f'Errore durante la predizione: {str(e)}')
            return func.HttpResponse(
                f"Prediction error: {str(e)}",
                status_code=500
            )
            
    except Exception as e:
        logging.error(f'Errore generale: {str(e)}')
        return func.HttpResponse(
            f"Internal server error: {str(e)}",
            status_code=500
        )