# German Public Broadcast Series Downloader

This project provides a Python script to download series from German public broadcasters via MediathekViewWeb.

## Setup

1. Dependencies: Install the required Python libraries:
   ```Bash
   pip install -r requirements.txt
   ```
2. `wget`: Ensure `wget` is installed and accessible in your system's PATH. This script uses `wget` for downloads.
3. **Configuration File**: Create a `config.yaml` file in the project's root directory. This file specifies which series to download and includes global settings.

## Configuration (config.yaml)

The config.yaml file defines the programs to download and global rate limits.

```yaml
programs:
  - name: die Anstalt
    min-length: 20
    season-offset: 2013
    max-age: 200

rate-limit: 250k
```

### Program Settings

Each item under `programs` is a series to be downloaded.

- `name`: (Required) The name of the series as it appears on MediathekViewWeb.
- `min-length`: (Optional) Minimum duration of an episode in minutes. Episodes shorter than this will be skipped.
- `season-offset`: (Optional) An integer offset applied to the detected season number. Use this if the season numbering in MediathekViewWeb does not match your desired local numbering. Defaults to `0`.
- `max-age`: (Optional) Maximum age of an episode in days. Episodes older than this will be skipped. Defaults to `365` days.

### Global Settings

- `rate-limit`: (Required) A string specifying the download speed limit for `wget`. For example, `250k` for 250 kilobytes/second or `2m` for 2 megabytes/second. This can be overridden at runtime.

# Usage

Run the script from your terminal:

```Bash
python download_series.py --out /path/to/your/download/folder
```

### Arguments

- `--out`, `-o`: (Required) Specifies the root directory where series will be downloaded. The script creates subfolders for each program and season within this directory.
- `--unlimited`: (Optional) If present, disables the download speed limit specified in `config.yaml`.
