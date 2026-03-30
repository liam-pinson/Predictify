import os
import librosa
import numpy as np
import pandas as pd
from pathlib import Path

# ─────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────
PROCESSED_DIR = Path("../data/processed/audio")
OUTPUT_CSV    = Path("../data/features/audio_features.csv")
SR            = 22050   # Sample rate (must match your FFmpeg output)
DURATION      = 30      # Seconds
N_MFCC        = 13      # Number of MFCC coefficients

# ─────────────────────────────────────────
# FEATURE EXTRACTION
# ─────────────────────────────────────────
def extract_features(file_path: Path) -> dict:
    """
    Extracts rhythm and spectral features from a single audio file.
    Returns a flat dictionary of features ready for a DataFrame row.
    """
    try:
        # Load audio (already normalized to 30s mono 22050Hz)
        y, sr = librosa.load(file_path, sr=SR, mono=True, duration=DURATION)

        # Pad if shorter than expected (e.g., track was < 45s total)
        target_len = SR * DURATION
        if len(y) < target_len:
            y = np.pad(y, (0, target_len - len(y)))

        features = {}

        # ── RHYTHM FEATURES ──────────────────────────────────────────
        # Tempo (BPM)
        tempo, beat_frames = librosa.beat.beat_track(y=y, sr=sr)
        tempo = np.atleast_1d(tempo)[0]  # Ensure scalar
        
        features["tempo"] = float(np.atleast_1d(tempo)[0])

        # Beat strength (how consistent/strong the beat is)
        onset_env = librosa.onset.onset_strength(y=y, sr=sr)
        features["beat_strength_mean"] = float(np.mean(onset_env))
        features["beat_strength_std"]  = float(np.std(onset_env))

        # Rhythm regularity (lower std = more regular beat)
        if len(beat_frames) > 1:
            beat_intervals = np.diff(librosa.frames_to_time(beat_frames, sr=sr))
            features["beat_regularity_mean"] = float(np.mean(beat_intervals))
            features["beat_regularity_std"]  = float(np.std(beat_intervals))
        else:
            features["beat_regularity_mean"] = 0.0
            features["beat_regularity_std"]  = 0.0

        # ── SPECTRAL FEATURES ─────────────────────────────────────────
        # Spectral Centroid (brightness of sound)
        spec_centroid = librosa.feature.spectral_centroid(y=y, sr=sr)[0]
        features["spectral_centroid_mean"] = float(np.mean(spec_centroid))
        features["spectral_centroid_std"]  = float(np.std(spec_centroid))

        # Spectral Bandwidth (range of frequencies)
        spec_bandwidth = librosa.feature.spectral_bandwidth(y=y, sr=sr)[0]
        features["spectral_bandwidth_mean"] = float(np.mean(spec_bandwidth))
        features["spectral_bandwidth_std"]  = float(np.std(spec_bandwidth))

        # Spectral Rolloff (frequency below which 85% of energy is contained)
        spec_rolloff = librosa.feature.spectral_rolloff(y=y, sr=sr, roll_percent=0.85)[0]
        features["spectral_rolloff_mean"] = float(np.mean(spec_rolloff))
        features["spectral_rolloff_std"]  = float(np.std(spec_rolloff))

        # Spectral Contrast (difference between peaks and valleys in spectrum)
        spec_contrast = librosa.feature.spectral_contrast(y=y, sr=sr)
        for i, band in enumerate(spec_contrast):
            features[f"spectral_contrast_band{i}_mean"] = float(np.mean(band))
            features[f"spectral_contrast_band{i}_std"]  = float(np.std(band))

        # Zero Crossing Rate (noisiness / percussiveness)
        zcr = librosa.feature.zero_crossing_rate(y)[0]
        features["zcr_mean"] = float(np.mean(zcr))
        features["zcr_std"]  = float(np.std(zcr))

        # RMS Energy (loudness)
        rms = librosa.feature.rms(y=y)[0]
        features["rms_mean"] = float(np.mean(rms))
        features["rms_std"]  = float(np.std(rms))

        # ── MFCC FEATURES ─────────────────────────────────────────────
        # MFCCs capture the overall "texture" and timbre of the audio
        mfccs = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=N_MFCC)
        for i, mfcc in enumerate(mfccs):
            features[f"mfcc_{i+1}_mean"] = float(np.mean(mfcc))
            features[f"mfcc_{i+1}_std"]  = float(np.std(mfcc))

        # ── CHROMA FEATURES ───────────────────────────────────────────
        # Chroma captures harmonic/melodic content (key, chord progressions)
        chroma = librosa.feature.chroma_stft(y=y, sr=sr)
        for i, chroma_band in enumerate(chroma):
            features[f"chroma_{i+1}_mean"] = float(np.mean(chroma_band))
            features[f"chroma_{i+1}_std"]  = float(np.std(chroma_band))

        # ── TONNETZ FEATURES ──────────────────────────────────────────
        # Tonal centroid features (harmonic relationships)
        harmonic = librosa.effects.harmonic(y)
        tonnetz = librosa.feature.tonnetz(y=harmonic, sr=sr)
        for i, t in enumerate(tonnetz):
            features[f"tonnetz_{i+1}_mean"] = float(np.mean(t))
            features[f"tonnetz_{i+1}_std"]  = float(np.std(t))

        return features

    except Exception as e:
        print(f"    💥 Feature extraction failed for {file_path.name}: {e}")
        return None


# ─────────────────────────────────────────
# MAIN PIPELINE
# ─────────────────────────────────────────
def build_feature_dataset():
    OUTPUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    rows = []
    extensions = {".wav", ".mp3", ".flac"}

    # Get subdirectories (hits, niche)
    categories = [d for d in PROCESSED_DIR.iterdir() if d.is_dir()]
    
    for category_dir in categories:
        label = category_dir.name
        files = [f for f in category_dir.rglob("*") if f.suffix.lower() in extensions]

        print(f"\n🎵 Processing [{label}] — {len(files)} files...")

        for i, file_path in enumerate(files):
            # --- PARSE ARTIST AND TITLE FROM FILENAME ---
            # Filename format: "Artist Name - Song Title.wav"
            filename_no_ext = file_path.stem 
            
            if " - " in filename_no_ext:
                artist, title = filename_no_ext.split(" - ", 1)
            else:
                artist, title = "Unknown", filename_no_ext

            print(f"  [{i+1}/{len(files)}] Extracting: {artist} - {title}")
            
            features = extract_features(file_path)

            if features is not None:
                # Add Metadata Columns
                features["artist"]    = artist.strip()
                features["song_title"] = title.strip()
                features["file_name"]  = file_path.name
                features["label"]      = label  # "hits" or "niche"
                rows.append(features)

    # Save to CSV
    df = pd.DataFrame(rows)
    
    # Reorder columns so metadata is at the front
    if not df.empty:
        cols = ["artist", "song_title", "label", "file_name"]
        feature_cols = [c for c in df.columns if c not in cols]
        existing_cols = [c for c in cols if c in df.columns]
        df = df[existing_cols + feature_cols]
    else:
        print("⚠️ No features were extracted. Check your audio files.")
    
    df.to_csv(OUTPUT_CSV, index=False)
    print(f"\n✨ Saved {len(rows)} tracks to: {OUTPUT_CSV}")
    return df


if __name__ == "__main__":
    build_feature_dataset()