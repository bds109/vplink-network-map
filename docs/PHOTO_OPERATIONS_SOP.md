# Map Photo Operations SOP

## Purpose

This SOP is for the operations team maintaining location photos without editing code or adding photo fields to the CSV.

## Responsibilities

1. Field/team members upload original photos to the internal shared drive using the existing State → Store folder structure.
2. Operations selects the photos intended for the online map and defines their display order.
3. Operations resizes/compresses the selected photos.
4. Operations renames and uploads the final files to Cloudflare R2.
5. The map reads the files automatically from the location `ID` in the CSV.

## File naming

For location ID `120`:

```text
120-01.jpg
120-02.jpg
120-03.jpg
```

Rules:

- use the latest CSV `ID`;
- use a hyphen, not an underscore;
- use two-digit sequence numbers;
- begin with `01`;
- do not skip a sequence number;
- use lowercase `.jpg`;
- `01` is the first/cover image shown in the popup.

Incorrect examples:

```text
120_01.jpg
120-1.jpg
120-01.png
120-01-final.jpg
```

## Image preparation

Recommended operational target:

- JPEG/JPG;
- long edge around 1600 px;
- web-appropriate quality around 75–85%;
- avoid files substantially larger than required for online viewing;
- retain original high-resolution photos in the internal shared drive.

## Cloudflare upload

Upload map-ready images to the `vplink-store-images` R2 bucket. All files may be stored in the bucket root because the location ID plus sequence makes each filename unique.

Current public test base URL:

```text
https://pub-3575d79a89e1428486f35743798eab42.r2.dev/
```

Example final URL:

```text
https://pub-3575d79a89e1428486f35743798eab42.r2.dev/120-01.jpg
```

## Updating photos

### Add another photo

If `120-01.jpg` and `120-02.jpg` already exist, upload the next image as:

```text
120-03.jpg
```

### Reorder photos

Rename/re-upload the files so the desired display order becomes `01`, `02`, `03`, etc.

### Remove a photo

After deletion, renumber later photos to keep the sequence continuous. For example, do not leave `01`, `02`, `04`; rename `04` to `03`.

### Location ID changes

When the CSV ID changes from a planning ID to a final location ID, rename every related R2 file.

Example:

```text
330-01.jpg → 180-01.jpg
330-02.jpg → 180-02.jpg
```

No code change and no additional CSV field is required.

## Validation

After upload:

1. Open the direct URL for `ID-01.jpg` in a browser.
2. Refresh the map.
3. Open the corresponding location popup.
4. Confirm all images appear in order.
5. Confirm the viewer returns from the last image to the first.

## Troubleshooting

### No photo area appears

Check:

- the CSV ID is correct;
- `{ID}-01.jpg` exists;
- filename uses a hyphen and two digits;
- extension is `.jpg`;
- direct R2 URL opens.

### Only early photos appear

The map stops at the first missing sequence. Check for a gap such as:

```text
120-01.jpg
120-03.jpg
```

Rename `120-03.jpg` to `120-02.jpg`.

### Wrong store photos appear

Compare the CSV `ID` with the number at the start of each R2 filename. Rename the files to match the current CSV.