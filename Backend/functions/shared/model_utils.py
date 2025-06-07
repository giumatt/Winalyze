import joblib
import io
from sklearn.ensemble import RandomForestClassifier
import pandas as pd
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, classification_report
import pickle
import logging
from typing import Tuple, Dict
import os
from azure.storage.blob import BlobServiceClient

def preprocess_data(df: pd.DataFrame, wine_type: str) -> Tuple[pd.DataFrame, bytes]:
    """
    Preprocessa il dataset applicando standardizzazione.
    
    Args:
        df (pd.DataFrame): DataFrame raw con i dati del vino
        wine_type (str): Tipo di vino ('red' o 'white')
        
    Returns:
        Tuple[pd.DataFrame, bytes]: (DataFrame preprocessato, scaler serializzato)
    """
    logging.info(f"Inizio preprocessing per vino {wine_type}")
    
    # Preprocessing
    df_cleaned = df.copy()
    df_cleaned.dropna(inplace=True)
    
    # Separazione features e target
    X = df_cleaned.drop('quality', axis=1)
    y = df_cleaned['quality']
    
    # Standardizzazione
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    
    # Ricostruzione DataFrame
    df_cleaned = pd.concat([
        pd.DataFrame(X_scaled, columns=X.columns),
        y.reset_index(drop=True)
    ], axis=1)
    
    # Serializza lo scaler
    scaler_bytes = pickle.dumps(scaler)
    
    logging.info(f"Preprocessing completato per vino {wine_type}")
    return df_cleaned, scaler_bytes

def train_model(df_cleaned: pd.DataFrame, wine_type: str) -> bytes:
    """
    Addestra il modello sui dati già preprocessati
    
    Args:
        df_cleaned (pd.DataFrame): DataFrame già preprocessato da cleaned
        wine_type (str): Tipo di vino ('red' o 'white')
        
    Returns:
        bytes: modello serializzato
    """
    logging.info(f"Inizio training per vino {wine_type}")
    
    # Separazione features e target
    X = df_cleaned.drop('quality', axis=1)
    y = df_cleaned['quality']
    
    # Split train/test per valutazione interna
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    
    # Training
    model = RandomForestClassifier(
        n_estimators=100,
        random_state=42,
        class_weight='balanced'
    )
    model.fit(X_train, y_train)
    
    # Log delle performance
    y_pred = model.predict(X_test)
    accuracy = accuracy_score(y_test, y_pred)
    logging.info(f"Accuracy su test set interno: {accuracy:.4f}")
    
    # Serializzazione
    model_bytes = pickle.dumps(model)
    
    logging.info(f"Training completato per vino {wine_type}")
    return model_bytes

def load_model(wine_type: str) -> Tuple[RandomForestClassifier, StandardScaler]:
    """
    Carica il modello e lo scaler dal blob storage
    
    Args:
        wine_type (str): Tipo di vino ('red' o 'white')
        
    Returns:
        Tuple[RandomForestClassifier, StandardScaler]: (modello, scaler)
    """
    try:
        connection_string = os.getenv("AzureWebJobsStorage")
        blob_service = BlobServiceClient.from_connection_string(connection_string)
        container_client = blob_service.get_container_client("models")

        model_blob = container_client.get_blob_client(f"model_{wine_type}.pkl")
        model_bytes = model_blob.download_blob().readall()

        scaler_blob = container_client.get_blob_client(f"scaler_{wine_type}.pkl")
        scaler_bytes = scaler_blob.download_blob().readall()

        model = joblib.load(io.BytesIO(model_bytes))
        scaler = joblib.load(io.BytesIO(scaler_bytes))

        logging.info(f"Modello e scaler caricati con successo per vino {wine_type}")
        return model, scaler

    except Exception as e:
        logging.error(f"Errore nel caricamento del modello: {str(e)}")
        raise