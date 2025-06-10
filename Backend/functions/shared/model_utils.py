import joblib
import io
from sklearn.ensemble import RandomForestClassifier
import pandas as pd
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score
import pickle
import logging
from typing import Tuple
import os
from azure.storage.blob import BlobServiceClient

def preprocess_data(df: pd.DataFrame, wine_type: str) -> Tuple[pd.DataFrame, bytes]:
    """
    Preprocess the dataset by applying standardization.
    
    Args:
        df (pd.DataFrame): Raw DataFrame with wine data
        wine_type (str): Type of wine ('red' or 'white')
        
    Returns:
        Tuple[pd.DataFrame, bytes]: (Preprocessed DataFrame, serialized scaler)
    """
    logging.info(f"Starting preprocessing for {wine_type} wine")
    
    # Data cleaning
    df_cleaned = df.copy()
    df_cleaned.dropna(inplace=True)
    
    # Separate features and target
    X = df_cleaned.drop('quality', axis=1)
    y = df_cleaned['quality']
    
    # Standardization
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    
    # Rebuild DataFrame with scaled features and target
    df_cleaned = pd.concat([
        pd.DataFrame(X_scaled, columns=X.columns),
        y.reset_index(drop=True)
    ], axis=1)
    
    # Serialize the scaler
    scaler_bytes = pickle.dumps(scaler)
    
    logging.info(f"Preprocessing completed for {wine_type} wine")
    return df_cleaned, scaler_bytes

def train_model(df_cleaned: pd.DataFrame, wine_type: str) -> bytes:
    """
    Train the model on preprocessed data.
    
    Args:
        df_cleaned (pd.DataFrame): Preprocessed DataFrame
        wine_type (str): Type of wine ('red' or 'white')
        
    Returns:
        bytes: serialized model
    """
    logging.info(f"Starting training for {wine_type} wine")
    
    # Separate features and target
    X = df_cleaned.drop('quality', axis=1)
    y = df_cleaned['quality']
    
    # Split train/test for internal evaluation
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    
    # Model training
    model = RandomForestClassifier(
        n_estimators=100,
        random_state=42,
        class_weight='balanced'
    )
    model.fit(X_train, y_train)
    
    # Log test set accuracy
    y_pred = model.predict(X_test)
    accuracy = accuracy_score(y_test, y_pred)
    logging.info(f"Test set accuracy: {accuracy:.4f}")
    
    # Serialization
    model_bytes = pickle.dumps(model)
    
    logging.info(f"Training completed for {wine_type} wine")
    return model_bytes

def load_model(wine_type: str) -> Tuple[RandomForestClassifier, StandardScaler]:
    """
    Load the model and scaler from blob storage.
    
    Args:
        wine_type (str): Type of wine ('red' or 'white')
        
    Returns:
        Tuple[RandomForestClassifier, StandardScaler]: (model, scaler)
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

        logging.info(f"Model and scaler successfully loaded for {wine_type} wine")
        return model, scaler

    except Exception as e:
        logging.error(f"Error loading model: {str(e)}")
        raise