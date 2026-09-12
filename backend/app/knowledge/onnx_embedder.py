"""ONNX implementation of the all-MiniLM-L6-v2 embedder."""

from pathlib import Path

import numpy as np
import onnxruntime as ort
from tokenizers import Tokenizer

from app.knowledge.embedder import Embedder


class OnnxEmbedder(Embedder):
    """Generate 384-dimensional embeddings using ONNX Runtime."""

    dimension = 384
    model_name = "all-MiniLM-L6-v2"
    max_length = 256

    def __init__(self, model_dir: str | Path) -> None:
        model_dir = Path(model_dir)

        model_path = model_dir / "model.onnx"
        tokenizer_path = model_dir / "tokenizer.json"

        if not model_path.exists():
            raise FileNotFoundError(f"ONNX model not found: {model_path}")

        if not tokenizer_path.exists():
            raise FileNotFoundError(
                f"Tokenizer not found: {tokenizer_path}"
            )

        self.tokenizer = Tokenizer.from_file(str(tokenizer_path))

        self.session = ort.InferenceSession(
            str(model_path),
            providers=["CPUExecutionProvider"],
        )

    async def embed(self, text: str) -> list[float]:
        """Generate a normalized embedding for one text."""

        encoded = self.tokenizer.encode(text)

        input_ids = encoded.ids[: self.max_length]
        attention_mask = encoded.attention_mask[: self.max_length]

        token_type_ids = [0] * len(input_ids)

        # Add padding if the sequence is shorter than max_length.
        padding_length = self.max_length - len(input_ids)

        if padding_length > 0:
            input_ids += [0] * padding_length
            attention_mask += [0] * padding_length
            token_type_ids += [0] * padding_length

        inputs = {
            "input_ids": np.array([input_ids], dtype=np.int64),
            "attention_mask": np.array(
                [attention_mask],
                dtype=np.int64,
            ),
            "token_type_ids": np.array(
                [token_type_ids],
                dtype=np.int64,
            ),
        }

        outputs = self.session.run(
            ["last_hidden_state"],
            inputs,
        )

        token_embeddings = outputs[0]

        attention = np.array(
            [attention_mask],
            dtype=np.float32,
        )[:, :, None]

        masked_embeddings = token_embeddings * attention

        summed_embeddings = masked_embeddings.sum(axis=1)

        token_count = attention.sum(axis=1)

        mean_embedding = summed_embeddings / np.maximum(
            token_count,
            1e-9,
        )

        # L2 normalization.
        norm = np.linalg.norm(mean_embedding, axis=1, keepdims=True)

        normalized_embedding = mean_embedding / np.maximum(
            norm,
            1e-12,
        )

        embedding = normalized_embedding[0]

        return embedding.astype(np.float32).tolist()