from google.cloud import storage
from datetime import timedelta
from django.conf import settings

def generate_signed_url(blob_name, bucket_name=settings.GS_BUCKET_NAME, expiration_minutes=1):
    """
    Génère une URL signée pour un fichier stocké sur Google Cloud Storage.
    """
    # Crée le client GCS
    client = storage.Client(project=settings.GS_PROJECT_ID, credentials=settings.GS_CREDENTIALS)
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(blob_name)

    # Génère l'URL signée
    url = blob.generate_signed_url(expiration=timedelta(minutes=expiration_minutes))
    return url
