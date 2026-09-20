"""Publish the repository's canonical agent guide with site-relative links."""
from pathlib import Path
import re


def on_post_build(config, **kwargs):
    text = Path(__file__).with_name('llms.txt').read_text()
    text = re.sub(r"\(docs/([\w-]+)\.md\)", r"(\1/)", text)
    (Path(config['site_dir']) / 'llms.txt').write_text(text)
