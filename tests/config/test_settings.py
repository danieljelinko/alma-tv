import yaml
from pathlib import Path
from alma_tv.config.settings import Settings

def test_yaml_config_loading(tmp_path, monkeypatch):
    """Test that settings are loaded from config.yaml."""
    # Create a temporary config.yaml
    config_data = {
        "media_root": "/tmp/test_media",
        "target_duration_minutes": 45
    }
    config_file = tmp_path / "config.yaml"
    config_file.write_text(yaml.dump(config_data))
    
    # Change working directory to tmp_path so Settings finds the config.yaml
    monkeypatch.chdir(tmp_path)
    
    # Reload settings
    settings = Settings()
    
    assert str(settings.media_root) == "/tmp/test_media"
    assert settings.target_duration_minutes == 45

def test_yaml_config_override_env(tmp_path, monkeypatch):
    """Test that env vars override config.yaml (standard Pydantic behavior)."""
    # Create a temporary config.yaml
    config_data = {
        "target_duration_minutes": 45
    }
    config_file = tmp_path / "config.yaml"
    config_file.write_text(yaml.dump(config_data))
    
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("ALMA_TARGET_DURATION_MINUTES", "50")
    
    settings = Settings()
    
    # Env vars should take precedence over YAML source if configured correctly
    # In our implementation: (init, yaml, env, dotenv, secret)
    # Pydantic sources are applied in reverse order? No, priority is first to last?
    # Wait, let's check Pydantic docs or behavior.
    # Usually: Init > Env > Dotenv > Secrets > Config file
    # My implementation: (init, yaml, env, dotenv, secret)
    # So Init overrides Yaml, Yaml overrides Env?
    # Let's verify the order.
    
    # If I want Env to override Yaml, Yaml should be AFTER Env?
    # Or is it priority based?
    # "The order of the sources in the list determines the priority."
    # "The first source in the list has the highest priority."
    
    # So (init, yaml, env) means Yaml overrides Env.
    # That might NOT be what we want. Usually Env overrides Config file.
    # So it should be (init, env, dotenv, yaml, secret)?
    # Let's test this behavior.
    
    assert settings.target_duration_minutes == 50
