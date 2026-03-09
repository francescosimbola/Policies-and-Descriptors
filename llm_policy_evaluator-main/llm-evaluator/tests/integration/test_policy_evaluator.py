import io
import csv
import json
import time
from pathlib import Path
from datetime import datetime
from importlib import resources

import pandas as pd
import pytest

from src.api import get_llm_evaluator


def _get_test_from_csv():
    with resources.as_file(resources.files("tests.integration.csv") / "test_4000_pair.csv") as f:
        content = io.StringIO(f.read_text())
    df = pd.read_csv(content)
    return list(df.itertuples(index=False, name=None))


# === NEW: CSV per-session con timestamp e appending riga-per-riga ===
@pytest.fixture(scope="session")
def results_file() -> Path:
    """
    Crea un file CSV unico per l'intera sessione di test:
    tests/integration/results/test_result_{YYYYmmdd_HHMMSS}.csv
    """
    results_dir = Path(__file__).resolve().parent / "results"
    results_dir.mkdir(parents=True, exist_ok=True)
    session_ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = results_dir / f"test_result_{session_ts}.csv"

    header = [
        "status_test",
        "duration_ms",
        "system_file_name",
        "policy_file_name",
        "expected_result",
        "actual_result",
        "timestamp",
        "error_response",
        "details_response",
    ]
    with open(path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(header)

    return path


@pytest.fixture
def append_result_row(results_file: Path):
    """
    Funzione helper che appende una riga al CSV della sessione.
    Serializza error/details in JSON per mantenerne la struttura.
    """
    def _append(*, status_test, duration_ms, system_file_name, policy_file_name, expected_result, actual_result, timestamp, error_response, details_response):
        with open(results_file, "a", newline="", encoding="utf-8") as fh:
            writer = csv.writer(fh)
            writer.writerow([
                status_test,
                duration_ms,
                system_file_name,
                policy_file_name,
                expected_result,
                actual_result,
                timestamp,
                json.dumps(error_response, ensure_ascii=False),
                json.dumps(details_response, ensure_ascii=False),
            ])
    return _append


@pytest.mark.parametrize("system_file_name, policy_file_name, expected", _get_test_from_csv())
def test_policy_evaluator(system_file_name, policy_file_name, expected, results_bag, append_result_row):
    llm_evaluator = get_llm_evaluator()
    policy = (resources.files("tests.integration.policies") / policy_file_name).read_text(encoding="utf-8")
    system = (resources.files("tests.integration.systems") / system_file_name).read_text(encoding="utf-8")

    ts = datetime.now().isoformat()
    start = time.monotonic()

    try:
        result = llm_evaluator.evaluate(system, policy)
        duration_ms = round((time.monotonic() - start) * 1000.0, 3)

        actual = result.satisfiesPolicy
        status_test = "passed" if (actual == expected) else "failed"

        # Scrivo SUBITO la riga
        append_result_row(
            status_test=status_test,
            duration_ms=duration_ms,
            system_file_name=system_file_name,
            policy_file_name=policy_file_name,
            expected_result=expected,
            actual_result=actual,
            timestamp=ts,
            error_response=result.errors,
            details_response=result.details,
        )

        # Mantengo il results_bag
        results_bag.actual_result = actual
        results_bag.timestamp = ts
        results_bag.error_response = result.errors
        results_bag.details_response = result.details

        assert actual == expected

    except Exception as e:
        duration_ms = round((time.monotonic() - start) * 1000.0, 3)
        # Loggo comunque il fallimento
        append_result_row(
            status_test="failed",
            duration_ms=duration_ms,
            system_file_name=system_file_name,
            policy_file_name=policy_file_name,
            expected_result=expected,
            actual_result=None,
            timestamp=ts,
            error_response=[str(e)],
            details_response=None,
        )
        raise


def test_synthesis(results_file: Path):
    """
    Non sovrascrive più nulla. Verifica soltanto che il CSV incrementale esista
    (i risultati vengono già salvati test-per-test in `results_file`).
    """
    assert results_file.exists()
    # Se vuoi vedere il path a fine run: esegui pytest con -s
    print(f"Incremental CSV: {results_file}")
