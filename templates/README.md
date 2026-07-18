# Example templates

Downloadable `.json` templates for Mosaic Collage Maker, listed on
[templates.html](../templates.html).

## Adding a new template

1. **Build the design in the app**, then use **Save as Template** (this strips
   out every photo reference — only the layout, text and pinning are kept).
2. **Copy the `.json` into this folder** with a descriptive, URL-friendly name,
   e.g. `travel-two-page.json`.
3. **Generate the preview thumbnail:**
   ```
   python3 tools/make_template_preview.py templates/your-template.json
   ```
   That writes `your-template.jpg` alongside it. Options: `--page 1` to preview a
   different design page, `--width 1400` for a larger image.
4. **Add a card** to `templates.html` — copy an existing `.card` block and update
   the image, title, description, meta chips (page size / design pages / frames
   per page / file size) and the download link.

Keep the `download` attribute on the link, otherwise browsers may display the
JSON rather than saving it.

## Watch the file size

A template that includes an **imported background image** embeds that image as
base64 inside the JSON, which makes it enormous — one local example came to
**31 MB** (29.6 MB of it the encoded background). Git keeps every version of a
file forever, so committing a few of those would permanently bloat this repo.

Prefer one of:

- publish **background-free** templates (the layout, text and pinning are the
  valuable part anyway);
- **downscale the background** before saving the template — 1–2 MB is ample;
- attach very large ones as **GitHub Release assets** instead, so they're
  downloadable without living in the repo history.

As a rule of thumb, a template with no background image is a few KB to a few
tens of KB. Anything in megabytes almost certainly has an image baked in.

## Compatibility

Templates carry a `version` field (currently `5`) plus their own page size and
DPI. Restoring one sets the app's page setup to match, so it's worth stating the
page size on each card.
