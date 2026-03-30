from audio_downloader import download_single_track, process_single_audio
from audio_features import extract_features
from model_service import predict_from_features

def run_spotify_inference(track_id: str):
    # 1. Download
    raw_audio = download_single_track(track_id)

    # 2. Process
    processed_audio = process_single_audio(raw_audio)

    # 3. Extract features
    features = extract_features(processed_audio)

    if features is None:
        raise Exception("Feature extraction failed")

    # 4. Predict
    prediction = predict_from_features(features)

    return {
        "track_id": track_id,
        "prediction": prediction,
        "features": features
    }