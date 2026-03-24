import torch
import torchaudio
from transformers import Wav2Vec2Processor, Wav2Vec2Model

MODEL_NAME = "facebook/wav2vec2-base-960h"

processor = Wav2Vec2Processor.from_pretrained(MODEL_NAME)
model = Wav2Vec2Model.from_pretrained(MODEL_NAME)
model.eval()


def load_audio(audio_path: str):
    waveform, sr = torchaudio.load(audio_path)
    if sr != 16000:
        waveform = torchaudio.functional.resample(waveform, sr, 16000)
    return waveform.squeeze()


def extract_embeddings(audio_path: str):
    waveform = load_audio(audio_path)

    inputs = processor(
        waveform.numpy(),
        sampling_rate=16000,
        return_tensors="pt"
    )

    with torch.no_grad():
        outputs = model(**inputs)

    return outputs.last_hidden_state.squeeze(0)