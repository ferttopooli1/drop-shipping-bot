import json
import os

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config.json")


def load_config():
  if not os.path.exists(CONFIG_PATH):
    cfg = {}
  else:
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
      cfg = json.load(f)
  if "language" not in cfg:
    cfg["language"] = "en"
  if "social_accounts" not in cfg:
    cfg["social_accounts"] = {}
  return cfg


def save_config(config_data):
  with open(CONFIG_PATH, "w", encoding="utf-8") as f:
    json.dump(config_data, f, indent=2, ensure_ascii=False)


def update_config_key(key_path: list, value: str):
  cfg = load_config()
  temp = cfg
  for key in key_path[:-1]:
    if key not in temp or not isinstance(temp[key], dict):
      temp[key] = {}
    temp = temp[key]
  temp[key_path[-1]] = value
  save_config(cfg)
