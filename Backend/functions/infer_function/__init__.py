import azure.functions as func
import logging
from shared.model_utils import load_model
import pandas as pd
import json

def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Inference request received')
    
    try:
        # Get and validate input data
        try:
            data = req.get_json()
            wine_type = data.pop("type", "").lower()
        except ValueError:
            return func.HttpResponse(
                "Invalid JSON in request body",
                status_code=400
            )

        # Validate wine type
        if wine_type not in ['red', 'white']:
            return func.HttpResponse(
                "Please specify 'type' as 'red' or 'white'",
                status_code=400
            )
        
        logging.info(f'Prediction request for {wine_type} wine')
        
        # Load the model
        try:
            model, scaler = load_model(wine_type)
            logging.info('Model loaded successfully')
        except Exception as e:
            logging.error(f'Error loading model: {str(e)}')
            return func.HttpResponse(
                f"Model loading error: {str(e)}",
                status_code=500
            )

        # Prepare data and make prediction
        try:
            df = pd.DataFrame([data])
            X_scaled = scaler.transform(df)
            prediction = model.predict(X_scaled)
            logging.info('Prediction completed successfully')
            
            return func.HttpResponse(
                json.dumps({"prediction": int(prediction[0])}),
                mimetype="application/json"
            )
        except Exception as e:
            logging.error(f'Error during prediction: {str(e)}')
            return func.HttpResponse(
                f"Prediction error: {str(e)}",
                status_code=500
            )
            
    except Exception as e:
        logging.error(f'General error: {str(e)}')
        return func.HttpResponse(
            f"Internal server error: {str(e)}",
            status_code=500
        )