from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[2]
SCRIPTS_DIR = ROOT_DIR / "scripts"


def test_expected_script_files_exist() -> None:
    expected = {
        "start-windows.bat",
        "stop-windows.bat",
        "start-linux.sh",
        "stop-linux.sh",
        "start-mac.sh",
        "stop-mac.sh",
    }

    actual = {p.name for p in SCRIPTS_DIR.iterdir() if p.is_file()}
    assert expected.issubset(actual)


def test_start_scripts_use_docker_compose_up() -> None:
    start_files = [
        SCRIPTS_DIR / "start-windows.bat",
        SCRIPTS_DIR / "start-linux.sh",
        SCRIPTS_DIR / "start-mac.sh",
    ]

    for script in start_files:
        text = script.read_text(encoding="utf-8")
        assert "docker compose up --build -d" in text


def test_stop_scripts_use_docker_compose_down() -> None:
    stop_files = [
        SCRIPTS_DIR / "stop-windows.bat",
        SCRIPTS_DIR / "stop-linux.sh",
        SCRIPTS_DIR / "stop-mac.sh",
    ]

    for script in stop_files:
        text = script.read_text(encoding="utf-8")
        assert "docker compose down" in text
