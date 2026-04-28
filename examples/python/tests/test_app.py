from src.app import main_entry


def test_main_entry():
    assert main_entry() == 1
