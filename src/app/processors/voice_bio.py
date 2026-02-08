"""Voice biometrics processor for speaker verification using SpeechBrain ECAPA-TDNN."""

import io
import logging
from typing import Any

import soundfile as sf
import torch
from speechbrain.inference.classifiers import EncoderClassifier

from app.config import get_settings
from app.processors.base import MediaProcessor, VerificationResult
from app.storage.s3_client import download_object

logger = logging.getLogger(__name__)

THRESHOLD = 0.30  # SpeechBrain ECAPA typical threshold for positive verification


class VoiceBioProcessor(MediaProcessor):
    """Voice biometrics processor using SpeechBrain ECAPA-TDNN for speaker verification."""

    def __init__(self) -> None:
        logger.info("Loading SpeechBrain ECAPA-TDNN model...")
        self.classifier = EncoderClassifier.from_hparams(
            source="speechbrain/spkrec-ecapa-voxceleb",
            savedir="./pretrained_models/spkrec-ecapa-voxceleb",
            run_opts={"device": "cpu"},
        )
        self.similarity = torch.nn.CosineSimilarity(dim=-1, eps=1e-6)
        logger.info("Voice model loaded.")

    @property
    def name(self) -> str:
        return "voice_bio"

    async def verify(
        self,
        media_bytes: bytes,
        subject_id: str,
        profile: str,
        metadata: dict[str, Any] | None = None,
    ) -> VerificationResult:
        if len(media_bytes) < 44:
            return VerificationResult(
                valid=False,
                confidence=0.0,
                reason="Invalid or empty audio",
                metadata={},
            )

        try:
            evidence_emb = self._extract_embeddings(media_bytes)

            ref_key = f"references/{subject_id}/enrollment.wav"
            settings = get_settings()
            try:
                ref_bytes = download_object(
                    bucket=settings.s3_bucket,
                    key=ref_key,
                    max_bytes=settings.max_download_bytes,
                )
                reference_emb = self._extract_embeddings(ref_bytes)
            except Exception as e:
                logger.warning("User %s not enrolled: %s", subject_id, e)
                return VerificationResult(
                    valid=False,
                    confidence=0.0,
                    reason="User has no voice enrollment (reference not found)",
                    metadata={"error": "reference_not_found"},
                )

            score = self._compare_embeddings(evidence_emb, reference_emb)
            # Cosine similarity is in [-1, 1]; normalize to [0, 1] and clamp (float can exceed 1.0)
            confidence = float(max(0.0, min(1.0, (score + 1) / 2)))
            is_valid = score >= THRESHOLD

            return VerificationResult(
                valid=is_valid,
                confidence=confidence,
                reason="Verification successful" if is_valid else "Voice does not match",
                metadata={
                    "processor": self.name,
                    "subject_id": subject_id,
                    "threshold_used": THRESHOLD,
                },
            )

        except Exception as e:
            logger.exception("Error in voice verification: %s", e)
            return VerificationResult(
                valid=False,
                confidence=0.0,
                reason=f"Internal AI error: {e!s}",
                metadata={"processor": self.name, "subject_id": subject_id},
            )

    def _extract_embeddings(self, audio_bytes: bytes) -> torch.Tensor:
        """Convert WAV bytes to waveform tensor then to 192-dim embedding vector."""
        with io.BytesIO(audio_bytes) as audio_file:
            data, _sample_rate = sf.read(audio_file, dtype="float32")
        # data: (samples,) or (samples, channels); we need (1, samples) for model
        if data.ndim == 1:
            signal = torch.from_numpy(data).unsqueeze(0)
        else:
            signal = torch.from_numpy(data.T).mean(dim=0, keepdim=True)

        embeddings = self.classifier.encode_batch(signal)
        return embeddings

    def _compare_embeddings(self, emb1: torch.Tensor, emb2: torch.Tensor) -> float:
        """Compute cosine similarity between two embeddings (range -1.0 to 1.0)."""
        score = self.similarity(emb1, emb2)
        return score.mean().item()
