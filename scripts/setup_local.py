"""Create private local settings with random credentials for Docker Compose."""

import secrets
from pathlib import Path


def main():
    target = Path('.env')
    if target.exists():
        raise SystemExit('.env already exists; it was not changed.')
    template = Path('.env.example').read_text(encoding='utf-8')
    for placeholder in (
        'change-me-db-password', 'change-me-root-password',
        'change-me-long-random-django-secret',
    ):
        template = template.replace(placeholder, secrets.token_urlsafe(64))
    with target.open('x', encoding='utf-8') as stream:
        stream.write(template)
    target.chmod(0o600)
    print('Created private .env. Review host and debug settings before deployment.')


if __name__ == '__main__':
    main()
