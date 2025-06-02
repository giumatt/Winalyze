import azure.functions as func
from azure.storage.blob import BlobServiceClient
import pandas as pd
from shared.preprocessing_utils import preprocess_dataset
from shared.model_utils import save_model
from sklearn.ensemble import RandomForestClassifier
import os
from dotenv import load_dotenv

load_dotenv()

def main(myblob: func.InputStream):
    metadata = myblob.metadata or {}
    wine_type = metadata.get('type', '').lower()

    if wine_type not in ['red', 'white']:
        raise ValueError("Metadata 'type' missing or not valid. Use 'red' or 'white'.")
    
    df = pd.read_csv(myblob)
    cleaned_df, scaler = preprocess_dataset(df)

    connection_string = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
    blob_service_client = BlobServiceClient.from_connection_string(connection_string)

    cleaned_blob = blob_service_client.get_blob_client(container="cleaned", blob=f"{wine_type}_cleaned.csv")
    cleaned_blob.upload_blob(cleaned_df.to_csv(index=False), overwrite=True)

    model = RandomForestClassifier(
        n_estimators=100,
        random_state=42,
        class_weight='balanced'
    )
    X = cleaned_df.drop("quality", axis=1)
    y = cleaned_df["quality"]
    model.fit(X, y)

    model_buffer = save_model(model, scaler)
    model_blob = blob_service_client.get_blob_client(container="models", blob=f"model_{wine_type}.pkl")
    model_blob .upload_blob(model_buffer.getvalue(), overwrite=True)