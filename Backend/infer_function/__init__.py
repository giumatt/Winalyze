import azure.functions as func
from azure.storage.blob import BlobServiceClient 
from shared.model_utils import load_model
import pandas as pd
import json
from dotenv import load_dotenv
import os

load_dotenv()

def main(req: func.HttpRequest) -> func.HttpResponse:
    try:
        data = req.get_json()
        wine_type = data.pop("type", "").lower()

        if wine_type not in ['red', 'white']:
            return func.HttpResponse("Please specify 'type' as 'red' or 'white'", status_code=400)
        
        connection_string = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
        blob_service_client = BlobServiceClient.from_connection_string(connection_string)
        blob_client = blob_service_client.get_blob_client(container="models", blob=f"model_{wine_type}.pkl")

        blob_bytes = blob_client.download_blob().readall()
        model, scaler = load_model(blob_bytes)

        df = pd.DataFrame([data])
        X_scaled = scaler.transform(df)

        prediction = model.predict(X_scaled)
        
        return func.HttpResponse(json.dumps({"prediction": int(prediction[0])}), mimetype="application/json")
    except Exception as e:
        return func.HttpResponse(f"Error: {str(e)}", status_code=500)