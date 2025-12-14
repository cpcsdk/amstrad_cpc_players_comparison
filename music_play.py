#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Convert a music file to a specific player format and replay it.

Usage examples:
  python music_play.py --music path/to/song.aks --player AKM
  python music_play.py --music path/to/song.aks --player FAP --m4 192.168.1.50
  python music_play.py --music path/to/song.aks --player AYT --emu ace
"""

import argparse
import logging
import os

from datasets import MusicFormat, convert_music_file
from players import PlayerFormat, crunch_music_file, build_replay_program
from player_utils import (
    parse_player,
    sanitize_filename,
    find_conversion_target,
    generate_conversion_paths,
)
from utils import execute_process, build_bndbuild_tokens


def _convert_and_build(music_path: str, player: PlayerFormat) -> dict:
    """Convert music and build replay program."""
    convert_to = find_conversion_target(music_path, player)

    # Check if the input is already in the target format
    input_fmt = MusicFormat.get_format(music_path)

    if convert_to == input_fmt:
        # No conversion needed - file is already in compatible format
        converted_fname = music_path
        logging.info(
            f"Music file is already in {convert_to.value} format, no conversion needed"
        )
        produced_fname = player.set_extension(converted_fname)
    else:
        # Generate output filenames
        converted_fname, produced_fname = generate_conversion_paths(
            music_path, convert_to, player
        )

        # Clean up any existing output files to ensure fresh conversion
        if os.path.exists(converted_fname):
            logging.debug(f"Removing existing file: {converted_fname}")
            os.remove(converted_fname)

        # Convert music to target format
        logging.info(f"Converting {music_path} to {convert_to.value}")
        convert_music_file(music_path, converted_fname)

        if not os.path.exists(converted_fname):
            raise RuntimeError(f"Conversion failed: {converted_fname} was not created")

    # If we didn't generate produced_fname in the else block, generate it now
    if "produced_fname" not in locals():
        produced_fname = player.set_extension(converted_fname)

    # Clean up existing player file
    if os.path.exists(produced_fname):
        logging.debug(f"Removing existing player file: {produced_fname}")
        os.remove(produced_fname)

    # Crunch/compress the music data
    logging.info(f"Crunching music data with {player.name}")
    res_conv = crunch_music_file(converted_fname, produced_fname, player)

    # Verify the crunched file was created
    if "compressed_fname" not in res_conv or not os.path.exists(
        res_conv["compressed_fname"]
    ):
        raise RuntimeError(f"Crunching failed: output file was not created")

    # Build replay program
    logging.info(f"Building replay program")
    res_play = build_replay_program(res_conv, player)

    return res_play


def _send_to_m4(sna_fname: str, m4_ip: str) -> None:
    """Send SNA file to M4 using bndbuild xfer."""
    logging.info(f"Sending {sna_fname} to M4 at {m4_ip}")

    tokens = build_bndbuild_tokens(
        "bndbuild", "--direct", "--", "xfer", m4_ip, "-y", sna_fname
    )

    execute_process(tokens)
    logging.info("File sent and launched on M4")


def _launch_emulator(sna_fname: str, emulator: str) -> None:
    """Launch emulator with the SNA file using bndbuild emu."""
    logging.info(f"Launching {emulator} with {sna_fname}")

    tokens = build_bndbuild_tokens(
        "bndbuild",
        "--direct",
        "--",
        "emu",
        "--emulator",
        emulator,
        "--snapshot",
        sna_fname,
        "run",
    )

    execute_process(tokens)
    logging.info("Emulator launched")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Convert a music file to a player format and replay it."
    )
    parser.add_argument(
        "--music",
        required=True,
        help="Path to the music file (AKS/CHP/YM/SKS/etc.)",
    )
    parser.add_argument(
        "--player",
        required=True,
        help="Player format to use (FAP/AYT/AKG/AKM/AKYS/AKYU/CHPB/etc.)",
    )
    parser.add_argument(
        "--m4",
        help="IP address of M4 board to send the SNA file to (e.g., 192.168.1.50)",
    )
    parser.add_argument(
        "--emu",
        help="Emulator to use for playing the SNA (ace/winape/cpcec/sugarbox/etc.)",
    )

    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")

    # Validate arguments
    if not os.path.exists(args.music):
        raise SystemExit(f"Music file not found: {args.music}")

    if not args.m4 and not args.emu:
        raise SystemExit("Either --m4 or --emu must be specified to replay the music.")

    try:
        player = parse_player(args.player)
    except ValueError as e:
        raise SystemExit(str(e))

    # Handle filenames with special characters
    music_path, needs_cleanup = sanitize_filename(args.music)
    original_path = args.music

    try:
        # Convert and build
        result = _convert_and_build(music_path, player)
        sna_fname = result["program_name"].replace(".BIN", ".sna")

        if not os.path.exists(sna_fname):
            raise SystemExit(f"SNA file not found: {sna_fname}")

        # Send to M4 or launch emulator
        if args.m4:
            _send_to_m4(sna_fname, args.m4)

        if args.emu:
            _launch_emulator(sna_fname, args.emu)

        logging.info("Done!")

    finally:
        # Cleanup sanitized file if created
        if needs_cleanup and os.path.exists(music_path) and music_path != original_path:
            try:
                os.remove(music_path)
                logging.debug(f"Cleaned up temporary file: {music_path}")
            except Exception:
                pass


if __name__ == "__main__":
    main()
