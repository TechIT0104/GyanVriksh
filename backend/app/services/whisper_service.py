"""Whisper large-v3 transcription with noise reduction and word timestamps.
GPU if available, CPU fallback."""
import logging

from app.config import settings

logger = logging.getLogger(__name__)

_model = None


def _get_model():
    global _model
    if _model is None:
        import whisper
        logger.info("Loading Whisper %s (first call is slow)...", settings.whisper_model)
        _model = whisper.load_model(settings.whisper_model)
    return _model


def denoise(audio_path: str) -> str:
    """Reduce plant-floor noise; writes a cleaned wav next to the original."""
    import librosa
    import noisereduce as nr
    import soundfile as sf
    y, sr = librosa.load(audio_path, sr=16000)
    y_clean = nr.reduce_noise(y=y, sr=sr)
    out_path = audio_path.rsplit(".", 1)[0] + "_clean.wav"
    sf.write(out_path, y_clean, sr)
    return out_path


def transcribe(audio_path: str, equipment_context: str = "") -> dict:
    """Returns {text, segments: [{start, end, text, words}], language}."""
    model = _get_model()
    try:
        clean_path = denoise(audio_path)
    except Exception:
        logger.warning("Denoise failed, using raw audio")
        clean_path = audio_path

    initial_prompt = (
        "This is an industrial maintenance expert discussing equipment "
        f"{equipment_context} pump seal maintenance OISD safety procedures. "
        "Speech may mix Hindi and English (Hinglish)."
    )
    result = model.transcribe(
        clean_path,
        task="transcribe",
        word_timestamps=True,
        initial_prompt=initial_prompt,
    )
    return {
        "text": result["text"].strip(),
        "language": result.get("language", "unknown"),
        "segments": [
            {
                "start": s["start"], "end": s["end"], "text": s["text"].strip(),
                "words": [{"word": w["word"], "start": w["start"], "end": w["end"]}
                          for w in s.get("words", [])],
            }
            for s in result.get("segments", [])
        ],
    }
