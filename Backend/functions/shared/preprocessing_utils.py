import pandas as pd
import io
import logging
from sklearn.preprocessing import StandardScaler
from azure.storage.blob import BlobServiceClient
import os

def preprocess(df: pd.DataFrame, wine_type: str):
    """
    Preprocessa il dataset per un tipo specifico di vino.
    
    Args:
        df (pd.DataFrame): DataFrame contenente i dati del vino
        wine_type (str): Tipo di vino ('red' o 'white')
        
    Returns:
        tuple: (DataFrame preprocessato, scaler addestrato)
    """
    logging.info(f"Preprocessing dataset for {wine_type} wine")
    
    # Rimozione valori nulli
    df.dropna(inplace=True)

    # Separazione features e target
    X = df.drop("quality", axis=1)
    y = df["quality"]

    # Standardizzazione
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    # Ricostruzione DataFrame
    df_cleaned = pd.concat([
        pd.DataFrame(X_scaled, columns=X.columns),
        y.reset_index(drop=True)
    ], axis=1)

    connection_string = os.getenv("AzureWebJobsStorage")
    blob_service = BlobServiceClient.from_connection_string(connection_string)
    
    cleaned_container = blob_service.get_container_client("cleaned")
    cleaned_blob = cleaned_container.get_blob_client(f"cleaned_{wine_type}.csv")
    cleaned_blob.upload_blob(
        df_cleaned.to_csv(index=False).encode(),  # Qui è stato corretto da cleaned a df_cleaned
        overwrite=True
    )

    logging.info(f"Dati preprocessati salvati per vino {wine_type}")
    return df_cleaned, scaler

def load_preprocessed_data(wine_type: str):
    try:
        connection_string = os.getenv("AzureWebJobsStorage")
        blob_service = BlobServiceClient.from_connection_string(connection_string)
        
        container_client = blob_service.get_container_client("cleaned")
        blob_client = container_client.get_blob_client(f"cleaned_{wine_type}.csv")
        
        csv_bytes = blob_client.download_blob().readall()
        cleaned = pd.read_csv(io.BytesIO(csv_bytes))

        logging.info(f"Dati preprocessati caricati per vino {wine_type}")
        return cleaned

    except Exception as e:
        logging.error(f"Errore nel caricamento dei dati preprocessati: {str(e)}")
        raise