"use client";

import { useState } from "react";

// ── Types ──────────────────────────────────────────────────────
type Track = {
  id: string;
  title: string;
  artist: string;
  album: string;
  image: string | null;
  preview_url: string | null;
  popularity: number;
};

// ── Main Page ──────────────────────────────────────────────────
export default function Home() {
  const [query, setQuery]             = useState("");
  const [results, setResults]         = useState<Track[]>([]);
  const [loading, setLoading]         = useState(false);
  const [error, setError]             = useState<string | null>(null);
  const [selected, setSelected]       = useState<Track | null>(null);

  // ── Prediction state ────────────────────────────────────────
  const [prediction, setPrediction]     = useState<any | null>(null);
  const [analyzing, setAnalyzing]       = useState(false);
  const [analyzeError, setAnalyzeError] = useState<string | null>(null);

  // ── Search handler ─────────────────────────────────────────
  const handleSearch = async () => {
    if (!query.trim()) return;
    setLoading(true);
    setError(null);
    setResults([]);
    setSelected(null);

    try {
      const res = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL}/search?q=${encodeURIComponent(query)}`
      );
      if (!res.ok) throw new Error("Search failed");
      const data: Track[] = await res.json();
      setResults(data);
    } catch (err) {
      setError("Could not connect to backend. Is FastAPI running?");
    } finally {
      setLoading(false);
    }
  };

  // ── Analyze handler ────────────────────────────────────────
  const handleAnalyze = async () => {
    if (!selected) return;

    setAnalyzing(true);
    setAnalyzeError(null);
    setPrediction(null);

    try {
      const res = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL}/predict/spotify`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ track_id: selected.id }),
        }
      );

      if (!res.ok) throw new Error(`Backend error: ${res.status}`);

      const data = await res.json();
      setPrediction(data);
    } catch (err) {
      setAnalyzeError(
        err instanceof Error ? err.message : "Prediction failed"
      );
    } finally {
      setAnalyzing(false);
    }
  };

  // ── Render ─────────────────────────────────────────────────
  return (
    <main className="min-h-screen bg-spotify-black text-spotify-text px-6 py-10">

      {/* Header */}
      <div className="max-w-2xl mx-auto mb-10 text-center">
        <h1 className="text-4xl font-bold text-spotify-green mb-2">
          🎵 Spotify Hit Predictor
        </h1>
        <p className="text-spotify-muted text-sm">
          Search for a track to analyze its hit potential
        </p>
      </div>

      {/* Search Bar */}
      <div className="max-w-2xl mx-auto flex gap-3 mb-6">
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && handleSearch()}
          placeholder="Search for a song..."
          className="flex-1 bg-spotify-card text-spotify-text placeholder-spotify-muted
                     rounded-full px-5 py-3 outline-none border border-transparent
                     focus:border-spotify-green transition"
        />
        <button
          onClick={handleSearch}
          className="bg-spotify-green text-black font-semibold px-6 py-3
                     rounded-full hover:scale-105 transition"
        >
          Search
        </button>
      </div>

      {/* Loading / Error */}
      {loading && (
        <p className="text-center text-spotify-muted mt-4">Searching...</p>
      )}
      {error && (
        <p className="text-center text-red-400 mt-4">{error}</p>
      )}

      {/* Results Dropdown List */}
      {results.length > 0 && !selected && (
        <div className="max-w-2xl mx-auto bg-spotify-dark rounded-xl overflow-hidden shadow-lg">
          {results.map((track) => (
            <div
              key={track.id}
              onClick={() => setSelected(track)}
              className="flex items-center gap-4 px-4 py-3 cursor-pointer
                         hover:bg-spotify-hover transition border-b border-spotify-card
                         last:border-none"
            >
              {track.image && (
                <img
                  src={track.image}
                  alt={track.album}
                  className="w-12 h-12 rounded object-cover"
                />
              )}
              <div className="flex-1 min-w-0">
                <p className="font-semibold truncate">{track.title}</p>
                <p className="text-spotify-muted text-sm truncate">{track.artist}</p>
              </div>
              <span className="text-spotify-muted text-xs">{track.album}</span>
            </div>
          ))}
        </div>
      )}

      {/* Selected Track Card */}
      {selected && (
        <div className="max-w-2xl mx-auto bg-spotify-card rounded-2xl p-6 shadow-xl">
          <div className="flex gap-5 items-start">
            {selected.image && (
              <img
                src={selected.image}
                alt={selected.album}
                className="w-28 h-28 rounded-xl object-cover shadow-md"
              />
            )}
            <div className="flex-1">
              <h2 className="text-2xl font-bold">{selected.title}</h2>
              <p className="text-spotify-muted">{selected.artist}</p>
              <p className="text-spotify-muted text-sm mt-1">{selected.album}</p>
              <div className="mt-3 flex items-center gap-2">
                <span className="text-xs text-spotify-muted">Popularity</span>
                <div className="flex-1 bg-spotify-hover rounded-full h-2">
                  <div
                    className="bg-spotify-green h-2 rounded-full"
                    style={{ width: `${selected.popularity}%` }}
                  />
                </div>
                <span className="text-xs text-spotify-green font-bold">
                  {selected.popularity}
                </span>
              </div>
            </div>
          </div>

          {/* ── ML Prediction Section ──────────────────────────── */}
          <div className="mt-6 bg-spotify-dark rounded-xl p-5">

            {/* Analyze Button — shown when no prediction yet */}
            {!prediction && (
              <div className="text-center">
                <button
                  onClick={handleAnalyze}
                  disabled={analyzing}
                  className="bg-spotify-green text-black font-semibold px-8 py-3
                             rounded-full hover:scale-105 transition disabled:opacity-50
                             disabled:cursor-not-allowed"
                >
                  {analyzing ? "Analyzing..." : "🔮 Analyze Hit Potential"}
                </button>
              </div>
            )}

            {/* Loading Message */}
            {analyzing && (
              <p className="text-center text-spotify-muted text-sm mt-3">
                Downloading and analyzing audio... this may take a moment.
              </p>
            )}

            {/* Error Message */}
            {analyzeError && (
              <p className="text-center text-red-400 text-sm mt-3">
                {analyzeError}
              </p>
            )}

            {/* Prediction Result */}
            {prediction && (
              <div className="text-center">
                <p className="text-spotify-muted text-xs mb-2 uppercase tracking-widest">
                  Prediction Result
                </p>
                <p className="text-4xl font-bold text-spotify-green mb-1">
                  {Math.round(prediction.prediction.hit_probability * 100)}%
                </p>
                <p className="text-lg font-semibold capitalize mb-4">
                  {prediction.prediction.prediction_label === "hit"
                    ? "🎯 Predicted Hit"
                    : "🎵 Niche Track"}
                </p>
                <button
                  onClick={() => setPrediction(null)}
                  className="text-spotify-muted text-xs underline hover:text-white transition"
                >
                  Analyze again
                </button>
              </div>
            )}

          </div>

          <button
            onClick={() => {
              setSelected(null);
              setPrediction(null);
              setAnalyzeError(null);
            }}
            className="mt-4 text-spotify-muted text-sm underline hover:text-white transition"
          >
            ← Back to results
          </button>
        </div>
      )}

    </main>
  );
}