"""SPC submission markdown parsing (no HTTP)."""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

__all__ = [
    'MAX_SPC_PROMPT_CHARS',
    'SAMPLE_KEY_PATTERN',
    'SpcSubmissionDraft',
    'compact_sample_output',
    'discover_submission_markdowns',
    'parse_submission_markdown',
]

MAX_SPC_PROMPT_CHARS = 10_000
SAMPLE_KEY_PATTERN = re.compile(r'^[A-Z]{2}[A-Z0-9]{10}\|[A-Z0-9]{4}$')


@dataclass
class SpcSubmissionDraft:
    source_file: Path
    name: str
    prompt: str
    model: str
    model_version: str
    update_frequency: str
    weight: float
    sample_output: str

    def to_payload(self) -> dict[str, object]:
        return {
            'name': self.name,
            'prompt': self.prompt,
            'model': self.model,
            'modelVersion': self.model_version,
            'updateFrequency': self.update_frequency,
            'weight': self.weight,
            'sampleOutput': self.sample_output,
        }


def _extract_section(text: str, header: str) -> str:
    pattern = rf'^## {re.escape(header)}\s*\n+(.*?)(?=^## |\Z)'
    match = re.search(pattern, text, re.MULTILINE | re.DOTALL)
    if not match:
        raise ValueError(f'missing section: ## {header}')
    return match.group(1).strip()


def _extract_fenced_block(section: str, lang: str | None = None) -> str:
    if lang:
        pattern = rf'```{re.escape(lang)}\s*\n(.*?)```'
    else:
        pattern = r'```(?:\w+)?\s*\n(.*?)```'
    match = re.search(pattern, section, re.DOTALL)
    if not match:
        raise ValueError(f'missing fenced block in section (lang={lang!r})')
    return match.group(1).strip()


def _first_line(section: str) -> str:
    for line in section.splitlines():
        stripped = line.strip()
        if stripped:
            return stripped
    raise ValueError('section is empty')


def _normalize_frequency(value: str) -> str:
    key = value.strip().lower()
    allowed = {'daily', 'weekly', 'monthly', 'quarterly'}
    if key not in allowed:
        raise ValueError(f'unknown update frequency: {value!r}')
    return key


def compact_sample_output(raw_json: str) -> str:
    parsed = json.loads(raw_json)
    if not isinstance(parsed, dict):
        raise ValueError('sample output must be a JSON object')
    if not parsed:
        raise ValueError('sample output must not be empty')
    for key, value in parsed.items():
        if not isinstance(key, str) or not SAMPLE_KEY_PATTERN.match(key):
            raise ValueError(f'invalid ISIN|MIC key: {key!r}')
        if not isinstance(value, (int, float)):
            raise ValueError(f'weight must be numeric: {key}={value!r}')
        if not -1 <= float(value) <= 1:
            raise ValueError(f'weight out of [-1, 1]: {key}={value!r}')
    gross_weight = sum(abs(float(value)) for value in parsed.values())
    if gross_weight <= 0:
        raise ValueError('sum(abs(weight)) must be > 0')
    return json.dumps(parsed, separators=(', ', ': '), ensure_ascii=False)


def parse_submission_markdown(path: Path | str, date_suffix: str) -> SpcSubmissionDraft:
    path = Path(path)
    text = path.read_text(encoding='utf-8')

    name = _first_line(_extract_section(text, 'Prompt Name'))
    model = _first_line(_extract_section(text, 'Model')).lower()
    model_version = _first_line(_extract_section(text, 'Model Version'))
    update_frequency = _normalize_frequency(_first_line(_extract_section(text, 'Update Frequency')))
    weight = float(_first_line(_extract_section(text, 'Prompt Weight')))

    prompt = _extract_fenced_block(_extract_section(text, 'Prompt'), 'text')
    if len(prompt) > MAX_SPC_PROMPT_CHARS:
        raise ValueError(f'{path.name}: prompt exceeds {MAX_SPC_PROMPT_CHARS} chars')

    sample_output = compact_sample_output(
        _extract_fenced_block(_extract_section(text, 'Sample Prompt Output'), 'json')
    )

    if not model_version:
        raise ValueError(f'{path.name}: model version is empty')

    return SpcSubmissionDraft(
        source_file=path,
        name=f'{name} {date_suffix}',
        prompt=prompt,
        model=model,
        model_version=model_version,
        update_frequency=update_frequency,
        weight=weight,
        sample_output=sample_output,
    )


def discover_submission_markdowns(spc_dir: Path | str, *, pattern: str = 'SPC Submission V*.md') -> list[Path]:
    spc_dir = Path(spc_dir)
    files = sorted(spc_dir.glob(pattern))
    if not files:
        raise FileNotFoundError(f'no files matching {pattern!r} under {spc_dir}')
    return files
