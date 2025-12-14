#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Shared utilities for player and music format operations.
"""

import logging
import os
import platform
import re
import shutil
from typing import List

from datasets import MusicFormat
from players import PlayerFormat


def escape_windows_path(path: str) -> str:
    """
    Escape file path for Windows bndbuild commands.
    
    On Windows, bndbuild requires backslashes to be escaped with double backslashes
    (\\\\) for proper path handling in shell commands.
    
    Args:
        path: File path to escape
        
    Returns:
        Escaped path on Windows, original path on other platforms
        
    Example:
        >>> escape_windows_path("C:\\Users\\file.bin")  # On Windows
        'C:\\\\\\\\Users\\\\\\\\file.bin'
        >>> escape_windows_path("/home/user/file.bin")  # On Linux
        '/home/user/file.bin'
    """
    if "Windows" in platform.system():
        return path.replace("\\", r"\\\\")
    return path


def parse_player(raw: str) -> PlayerFormat:
    """
    Parse a single player format from string.
    
    Args:
        raw: Player format string (e.g., "AKM", "fap", "FAP")
        
    Returns:
        PlayerFormat enum value
        
    Raises:
        ValueError: If format is unknown
    """
    t = raw.strip().upper()

    # Try enum name first (AKM, FAP, etc.)
    try:
        return PlayerFormat[t]
    except KeyError:
        pass

    # Try by value
    for pf in PlayerFormat:
        if pf.value.lower() == raw.lower():
            return pf

    raise ValueError(f"Unknown player format: {raw}")


def parse_players(raw: str | None) -> List[PlayerFormat] | None:
    """
    Parse comma-separated list of player formats.
    
    Args:
        raw: Comma-separated player formats (e.g., "AKM,FAP,AYT") or None
        
    Returns:
        List of PlayerFormat enums, or None if raw is None
        
    Raises:
        ValueError: If any format is unknown
    """
    if raw is None:
        return None
    result: List[PlayerFormat] = []
    for token in raw.split(","):
        t = token.strip()
        if not t:
            continue
        result.append(parse_player(t))
    return result


def sanitize_filename(path: str) -> tuple[str, bool]:
    """
    Create a sanitized version of a file path if needed.
    
    This function handles filenames with problematic characters (spaces, ampersands)
    by creating a symlink (or copy if symlinks are not supported) with sanitized name.
    
    Args:
        path: Original file path
        
    Returns:
        Tuple of (sanitized_path, needs_cleanup)
        - sanitized_path: Path to use (original if no sanitization needed)
        - needs_cleanup: True if a temporary file was created and should be removed later
    """
    if "&" not in os.path.basename(path) and " " not in os.path.basename(path):
        return path, False

    base_dir = os.path.dirname(path) or "."
    base_name = os.path.basename(path)
    name, ext = os.path.splitext(base_name)

    # Replace problematic characters
    safe_name = re.sub(r"[&\s]+", "_", name)
    safe_path = os.path.join(base_dir, safe_name + ext)

    # Create symlink or copy
    if not os.path.exists(safe_path) or not os.path.samefile(path, safe_path):
        try:
            os.symlink(os.path.abspath(path), safe_path)
            logging.info(f"Created symlink: {safe_path} -> {path}")
        except (OSError, NotImplementedError):
            shutil.copy2(path, safe_path)
            logging.info(f"Created copy: {safe_path}")
        return safe_path, True

    return safe_path, False


def find_compatible_players(
    music_path: str, requested_players: List[PlayerFormat] | None = None
) -> List[PlayerFormat]:
    """
    Find all players compatible with a music file.
    
    Args:
        music_path: Path to the music file
        requested_players: Optional list of specific players to check, or None for all
        
    Returns:
        List of compatible PlayerFormat values
    """
    input_fmt = MusicFormat.get_format(music_path)
    convertible = input_fmt.convertible_to()
    candidates = requested_players if requested_players is not None else list(PlayerFormat)
    
    compatible: List[PlayerFormat] = []
    for pf in candidates:
        if pf in [PlayerFormat.AYC]:
            continue  # not yet supported
        expected = pf.requires_one_of()
        if convertible.intersection(expected):
            compatible.append(pf)
    return compatible


def find_conversion_target(music_path: str, player: PlayerFormat) -> MusicFormat:
    """
    Determine the target format for converting a music file to a player format.
    
    Args:
        music_path: Path to the music file
        player: Target player format
        
    Returns:
        MusicFormat to convert to
        
    Raises:
        ValueError: If the music file is not compatible with the player
    """
    input_fmt = MusicFormat.get_format(music_path)
    convertible = input_fmt.convertible_to()
    expected = player.requires_one_of()

    targets = sorted(convertible.intersection(expected), key=lambda f: f.value)
    if not targets:
        raise ValueError(
            f"Music file '{music_path}' (format: {input_fmt.value}) is not "
            f"compatible with player {player.name}. Player requires one of: "
            f"{', '.join(f.value for f in expected)}"
        )

    return targets[0]


def generate_conversion_paths(
    music_path: str, convert_to: MusicFormat, player: PlayerFormat
) -> tuple[str, str]:
    """
    Generate file paths for the conversion pipeline.
    
    Args:
        music_path: Original music file path
        convert_to: Target music format to convert to
        player: Target player format
        
    Returns:
        Tuple of (converted_path, produced_path)
        - converted_path: Path for the converted music file
        - produced_path: Path for the player-specific output file
    """
    converted_fname = music_path.replace(
        os.path.splitext(music_path)[1], f".{convert_to.value}"
    )
    produced_fname = player.set_extension(converted_fname)
    return converted_fname, produced_fname
