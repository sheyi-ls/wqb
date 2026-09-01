from collections.abc import Generator, Iterable
from typing import Any

from .constants import (
    EQUITY,
    Alpha,
    MultiAlpha,
    Region,
    Delay,
    Universe,
    InstrumentType,
    Language,
    Neutralization,
    UnitHandling,
    NanHandling,
    Pasteurization,
)
from .urls import WQB_API_URL

__all__ = [
    'to_multi_alphas',
    'build_regular_alpha',
    'coerce_multi_targets',
    'simulation_ref_url',
]

def to_multi_alphas(
    alphas: Iterable[Alpha],
    multiple: int | Iterable[Any],
) -> Generator[MultiAlpha, None, None]:
    """
    Converts an iterable series of `Alpha` objects to an iterable series
    of `MultiAlpha` objects.

    Parameters
    ----------
    alphas: Iterable[Alpha]
        The iterable series of `Alpha` objects.
    multiple: int | Iterable[Any]
        The number of `Alpha` objects to be grouped into a `MultiAlpha`
        object. If *int*, the `Alpha` objects are grouped by it. If
        *Iterable[Any]*, the `Alpha` objects are grouped by its length.

    Returns
    -------
    Iterable[MultiAlpha]
        An iterable series of `MultiAlpha` objects.

    Examples
    --------
    >>> alphas = [{...} for _ in range(6)]
    >>> alphas
    [{...}, {...}, {...}, {...}, {...}, {...}]
    >>> multi_alphas = list(wqb.to_multi_alphas(alphas, 3))
    >>> multi_alphas
    [[{...}, {...}, {...}], [{...}, {...}, {...}]]
    """
    alphas = iter(alphas)
    multiple = range(multiple) if isinstance(multiple, int) else tuple(multiple)
    try:
        while True:
            multi_alpha = []
            for _ in multiple:
                multi_alpha.append(next(alphas))
            yield multi_alpha
    except StopIteration as e:
        if 0 < len(multi_alpha):
            yield multi_alpha



def build_regular_alpha(
    expression: str,
    *,
    instrument_type: InstrumentType = EQUITY,
    region: Region = 'USA',
    universe: Universe = 'TOP3000',
    delay: Delay = 1,
    decay: int = 4,
    neutralization: Neutralization = 'INDUSTRY',
    truncation: float = 0.0,
    pasteurization: Pasteurization = 'ON',
    unit_handling: UnitHandling = 'VERIFY',
    nan_handling: NanHandling = 'OFF',
    language: Language = 'FASTEXPR',
    visualization: bool = False,
    test_period: str = 'P0Y0M',
    max_trade: str = 'OFF',
    lookback: int | None = None,
    **settings,
) -> Alpha:
    """
    Build a REGULAR `Alpha` dict with BRAIN-compatible settings.

    Notes
    -----
    When *language* is ``FASTEXPR``, ``unitHandling`` and ``nanHandling`` are
    included. When *language* is ``PYTHON``, ``lookback`` defaults to 256.
    Extra ``settings`` entries are merged into the settings block (camelCase
    keys such as ``instrumentType`` are also accepted).
    """
    normalized_language = str(language).upper()
    alpha_settings: dict[str, Any] = {
        'instrumentType': instrument_type,
        'region': region,
        'universe': universe,
        'delay': delay,
        'decay': decay,
        'neutralization': neutralization,
        'truncation': truncation,
        'pasteurization': pasteurization,
        'language': normalized_language,
        'visualization': visualization,
        'testPeriod': test_period,
        'maxTrade': max_trade,
    }
    if normalized_language == 'PYTHON':
        alpha_settings['lookback'] = 256 if lookback is None else lookback
    else:
        alpha_settings['unitHandling'] = unit_handling
        alpha_settings['nanHandling'] = nan_handling
    alpha_settings.update(settings)
    return {
        'type': 'REGULAR',
        'settings': alpha_settings,
        'regular': expression,
    }



def coerce_multi_targets(
    targets: MultiAlpha | Iterable[Alpha | str],
    *,
    settings: dict[str, Any] | None = None,
    **settings_kwargs,
) -> MultiAlpha:
    merged_settings = dict(settings or {})
    merged_settings.update(settings_kwargs)
    multi: MultiAlpha = []
    for target in targets:
        if isinstance(target, str):
            multi.append(build_regular_alpha(target, **merged_settings))
        elif isinstance(target, dict):
            multi.append(target)
        else:
            raise TypeError(
                'multi_simulate targets must be Alpha dicts or expression strings'
            )
    if not 2 <= len(multi) <= 10:
        raise ValueError(f'multi_simulate requires 2-10 alphas, got {len(multi)}')
    return multi



def simulation_ref_url(ref: str) -> str:
    if ref.startswith('http'):
        return ref
    return f"{WQB_API_URL}/simulations/{ref}"


