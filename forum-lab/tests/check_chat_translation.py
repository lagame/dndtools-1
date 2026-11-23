"""Ensure the installed LiteChat translation covers all source labels and placeholders."""

import json
import re
import subprocess


FILES = (
    "acp_chat.php",
    "common.php",
    "ucp_chat.php",
    "permissions_chat.php",
    "info_acp_chat.php",
    "info_ucp_chat.php",
)
PLACEHOLDER = re.compile(r"%(?:\d+\$)?[a-z]", re.I)


def read_language(locale, filename):
    path = f"/var/www/html/ext/stoker/chat/language/{locale}/{filename}"
    php = f"define('IN_PHPBB', true); $lang=[]; include {json.dumps(path)}; echo json_encode($lang);"
    result = subprocess.run(
        ["docker", "exec", "dndtools-forum_lab-1", "php", "-r", php],
        check=True, capture_output=True, text=True,
    )
    return json.loads(result.stdout)


def check_values(source, translated, label):
    if isinstance(source, dict):
        assert isinstance(translated, dict), f"{label}: expected mapping"
        assert source.keys() == translated.keys(), f"{label}: missing or extra keys"
        for key in source:
            check_values(source[key], translated[key], f"{label}.{key}")
    elif isinstance(source, str):
        assert isinstance(translated, str) and translated, f"{label}: empty translation"
        assert sorted(PLACEHOLDER.findall(source)) == sorted(PLACEHOLDER.findall(translated)), (
            f"{label}: placeholders differ"
        )


def main():
    total = 0
    for filename in FILES:
        source = read_language("en", filename)
        translated = read_language("pt_br", filename)
        check_values(source, translated, filename)
        total += len(source)
    print(f"All {total} LiteChat labels match the PT-BR translation.")


if __name__ == "__main__":
    main()
