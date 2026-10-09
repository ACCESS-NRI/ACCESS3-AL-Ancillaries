# Change the URL segment for pages in MkDocs to hide the "/pages" prefix, so that pages inside the
# "pages" directory are served directly at the root URL.
# This is done in `on_files`, before any page is built, so that every page (including nav links and
# links between pages) sees the final URLs regardless of the order the pages are built in.
import os
from mkdocs.plugins import event_priority

PAGES_PREFIX = "pages/"

@event_priority(-100)
def on_files(files, config):
    for file in files.documentation_pages():
        if file.src_uri.startswith(PAGES_PREFIX):
            file.url = file.url.removeprefix(PAGES_PREFIX)
            file.dest_uri = file.dest_uri.removeprefix(PAGES_PREFIX)
            file.abs_dest_path = os.path.normpath(os.path.join(config.site_dir, file.dest_uri))
    return files
