"""Read a local folder of .eml files and save their PDF attachments.

A real deployment would read from IMAP. Reading saved .eml files keeps the
project runnable offline, and the parsing code is the same either way:
Python's standard `email` module.
"""
from __future__ import annotations

from email import policy
from email.message import EmailMessage
from email.parser import BytesParser
from pathlib import Path


def build_email(pdf_path: Path, sender: str, subject: str) -> bytes:
    """Wrap one PDF in an email, the way a vendor would send it."""
    msg = EmailMessage()
    msg["From"] = sender
    msg["To"] = "accounts@greenleaf.example"
    msg["Subject"] = subject
    msg.set_content("Please find the invoice attached.\n")
    msg.add_attachment(pdf_path.read_bytes(), maintype="application", subtype="pdf", filename=pdf_path.name)
    return msg.as_bytes()


def collect_attachments(mailbox_dir: Path, inbox_dir: Path) -> list[dict]:
    """Save every PDF attachment found in mailbox_dir/*.eml into inbox_dir.

    Returns one record per attachment so the pipeline knows which email each
    PDF came from.
    """
    inbox_dir.mkdir(parents=True, exist_ok=True)
    found = []
    for eml in sorted(mailbox_dir.glob("*.eml")):
        msg = BytesParser(policy=policy.default).parsebytes(eml.read_bytes())
        for part in msg.iter_attachments():
            if part.get_content_type() != "application/pdf":
                continue
            # Prefix with the email's file name so two emails carrying the same
            # attachment name don't overwrite each other.
            target = inbox_dir / f"{eml.stem}__{part.get_filename()}"
            target.write_bytes(part.get_payload(decode=True))
            found.append({"email_file": eml.name, "from": str(msg["From"]), "subject": str(msg["Subject"]), "pdf": target})
    return found
