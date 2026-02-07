"""Basic tests for the punie package."""


def test_punie_module_has_correct_name():
    """Test that punie module can be imported and has correct __name__."""
    import punie

    assert punie.__name__ == "punie"
