import azure.functions as func
import logging

def main(inputblob: func.InputStream):
    logging.info(f"🚨 TEST TRIGGER ATTIVATO: {inputblob.name}")