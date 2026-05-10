"""Email-domain helpers for org assignment.

Generic free-mail domains map to a "personal" (solo) org since same-domain has
no team meaning. Anything else is treated as a work domain and members on it
share a single org and can invite teammates.
"""

GENERIC_MAIL_DOMAINS: frozenset[str] = frozenset({
    "gmail.com",
    "googlemail.com",
    "outlook.com",
    "hotmail.com",
    "live.com",
    "msn.com",
    "yahoo.com",
    "yahoo.co.uk",
    "ymail.com",
    "icloud.com",
    "me.com",
    "mac.com",
    "aol.com",
    "proton.me",
    "protonmail.com",
    "pm.me",
    "tutanota.com",
    "tutanota.de",
    "tuta.io",
    "fastmail.com",
    "fastmail.fm",
    "gmx.com",
    "gmx.de",
    "gmx.net",
    "mail.com",
    "zoho.com",
    "zohomail.com",
    "yandex.com",
    "yandex.ru",
    "qq.com",
    "163.com",
    "126.com",
    "duck.com",
    "hey.com",
})


def domain_from_email(email: str) -> str:
    """Lowercased domain part of an email; empty string if malformed."""
    if not email or "@" not in email:
        return ""
    return email.rsplit("@", 1)[1].strip().lower()


def is_generic_domain(domain: str) -> bool:
    return domain.lower() in GENERIC_MAIL_DOMAINS
