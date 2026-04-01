from audio_downloader import download_single_track, process_single_audio
from audio_features import extract_features
from model_service import predict_from_features
from gemini_agent import generate_hit_summary
import os
from pathlib import Path
import shutil
import glob

def run_spotify_inference(track_id: str):
    raw_audio = None
    processed_audio = None

    try:
        # 1. Download
        print("pre download")
        raw_audio = download_single_track(track_id)
        print("post download")

        # 2. Process (this already deletes raw_audio internally)
        processed_audio = process_single_audio(raw_audio)
        raw_audio = None  # already cleaned up by process_single_audio

        # 3. Extract features
        features = extract_features(processed_audio)
        if features is None:
            raise Exception("Feature extraction failed")

        # 4. Predict
        prediction = predict_from_features(features)

        # 5. Generate Gemini Summary
        summary, model_used = generate_hit_summary(features, prediction)

        return {
            "track_id": track_id,
            "prediction": prediction,
            "features": features,
            "summary": summary,
            "gemini_model": model_used
        }

    finally:
        # Clean up processed audio file
        if processed_audio and os.path.exists(processed_audio):
            os.remove(processed_audio)
            print(f"🧹 Cleaned up: {processed_audio}")

        # Clean up any leftover temp_inference folders
        for folder in Path(".").glob("temp_inference_*"):
            shutil.rmtree(folder, ignore_errors=True)
            print(f"🧹 Cleaned up folder: {folder}")

        # Clean up any leftover temp_processed files
        for f in Path(".").glob("temp_processed_*.wav"):
            os.remove(f)
            print(f"🧹 Cleaned up: {f}")