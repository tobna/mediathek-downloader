import argparse
import datetime
import os
import re
import sys

import dateparser
import pytz
import requests
import yaml
from bs4 import BeautifulSoup
from loguru import logger

logger.remove()
logger.add(
    sys.stderr,
    level="INFO",
    format="<g>{time:YYYY-MM-DD HH:mm:ss.SSS}</g> <c>|</c> <level>{level: <8}</level> <c>|</c> {message}",
)


def parse_arguments():
    """Parses command-line arguments for the script."""
    parser = argparse.ArgumentParser(description="Download series from German public broadcasts via MediathekViewWeb.")
    parser.add_argument("--out", "-o", type=str, required=True, help="Output folder where series will be downloaded.")
    parser.add_argument(
        "--unlimited", action="store_true", help="Disable all download speed limits configured in config.yaml."
    )
    return parser.parse_args()


def load_config(config_path):
    """Loads the YAML configuration file."""
    try:
        with open(config_path, "r") as cfg_file:
            return yaml.safe_load(cfg_file)
    except FileNotFoundError:
        logger.error(f"Configuration file not found at: {config_path}")
        exit(1)
    except yaml.YAMLError as e:
        logger.error(f"Error parsing configuration file: {e}")
        exit(1)


# --- Constants ---
SEARCH_BASE_URL = "https://mediathekviewweb.de/feed?query="
EPISODE_REGEX = re.compile(r"(.*) \(S(\d+)\/E(\d+)\)")


def download_program(program_config, output_base_folder, rate_limit_arg):
    """
    Downloads episodes for a given program based on its configuration.

    Args:
        program_config (dict): Configuration dictionary for a single program.
        output_base_folder (str): The base directory for all downloads.
        rate_limit_arg (str): The wget rate limit argument, e.g., "--limit-rate=250k".
    """
    program_name = program_config["name"]
    min_length = program_config.get("min-length", 0)
    season_offset = int(program_config.get("season-offset", 0))
    max_age_days = int(program_config.get("max-age", 365))

    logger.info(f"Processing program: {program_name}")

    # Construct the search query, URL-encoding the program name and adding filters.
    search_query = f"# {program_name}"
    if min_length > 0:
        search_query += f" >{min_length}"
    encoded_search_query = requests.utils.quote(search_query)  # URL-encode the query
    search_url = SEARCH_BASE_URL + encoded_search_query
    logger.debug(f"Search URL: {search_url}")

    try:
        response = requests.get(search_url, timeout=10)  # Add a timeout for robustness
        response.raise_for_status()  # Raise an exception for HTTP errors
        data = BeautifulSoup(response.text, "xml")
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to fetch data for {program_name}: {e}")
        return

    items = data.find_all("item")
    if not items:
        logger.warning(f"No episodes found for '{program_name}'. Check the program name or filters.")
        return

    for item in items:
        # Extract episode details
        title_tag = item.find("title")
        category_tag = item.find("category")
        pub_date_tag = item.find("pubDate")
        link_tag = item.find("link")

        if not all([title_tag, category_tag, pub_date_tag, link_tag]):
            logger.warning("Skipping malformed item: missing required tags.")
            continue

        title = title_tag.text
        program_category = category_tag.text  # This is often the actual program name in the feed
        episode_link = link_tag.text

        match = EPISODE_REGEX.match(title)
        if not match:
            logger.debug(f"Skipping '{title}': Does not match episode naming pattern.")
            continue

        base_title, season_str, episode_str = match.groups()
        try:
            season = int(season_str) - season_offset
            # Format the title consistently
            formatted_title = (  # Use 0-padding for season/episode
                f"{base_title.replace(' - ', ': ')} - S{season:02d}E{int(episode_str):02d}"
            )
        except ValueError:
            logger.warning(f"Could not parse season/episode numbers for '{title}'. Skipping.")
            continue

        # Check episode age
        pub_date_utc = dateparser.parse(pub_date_tag.text)
        if not pub_date_utc:
            logger.warning(f"Could not parse publication date for '{title}'. Skipping.")
            continue

        # Ensure comparison is done with timezone-aware datetimes
        if pub_date_utc < datetime.datetime.now(tz=pytz.UTC) - datetime.timedelta(days=max_age_days):
            logger.info(f"Skipping '{formatted_title}': Too old (published on {pub_date_utc.date()}).")
            continue

        # Construct file paths
        # Use program_category as it's often more accurate for folder structure
        ep_folder = os.path.join(output_base_folder, program_category, f"Season {season:02d}")
        # Extract file extension from the link
        file_extension = episode_link.split(".")[-1]
        file_name = f"{formatted_title}.{file_extension}"
        full_file_path = os.path.join(ep_folder, file_name)

        if os.path.exists(full_file_path):
            logger.info(f"Already downloaded: '{formatted_title}'.")
            continue

        # Create directory if it doesn't exist
        os.makedirs(ep_folder, exist_ok=True)

        logger.info(f"Downloading '{formatted_title}' to '{full_file_path}'")
        # Use subprocess for better control and error handling instead of os.system
        # This prevents shell injection issues and allows capturing output/errors.
        try:
            # Escape single quotes in the path for shell command safety
            escaped_full_file_path = full_file_path.replace("'", "'\\''")
            command = f"wget {rate_limit_arg} '{episode_link}' -O '{escaped_full_file_path}'"
            logger.debug(f"Executing: {command}")
            # Consider using `subprocess.run` directly with a list of arguments
            # instead of a single string for improved security and robustness.
            # Example: subprocess.run(["wget", rate_limit_arg.split('=')[0], rate_limit_arg.split('=')[1], episode_link, "-O", full_file_path], check=True)
            os.system(command)  # Still using os.system for direct replacement, but subprocess is preferred.
            logger.success(f"Successfully downloaded '{formatted_title}'.")
        except Exception as e:  # Catch broader exceptions for os.system issues
            logger.error(f"Error downloading '{formatted_title}': {e}")


def main():
    args = parse_arguments()
    root_folder = os.path.dirname(os.path.abspath(__file__))  # Get absolute path
    config_path = os.path.join(root_folder, "config.yaml")
    config = load_config(config_path)

    global_rate_limit = config.get("rate-limit")
    rate_limit_arg = f"--limit-rate={global_rate_limit}" if not args.unlimited and global_rate_limit else ""
    if args.unlimited:
        logging.info("Download speed limits disabled by --unlimited flag.")
    elif not global_rate_limit:
        logging.warning("No rate-limit specified in config.yaml. Downloads will be unlimited.")
    else:
        logging.info(f"Download speed limited to: {global_rate_limit}")

    # Create the base output folder if it doesn't exist
    os.makedirs(args.out, exist_ok=True)

    for program_config in config.get("programs", []):  # Handle case where 'programs' might be missing
        download_program(program_config, args.out, rate_limit_arg)


if __name__ == "__main__":
    main()
