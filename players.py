#!/usr/bin/env python3
# -*- coding: utf-8 -*-


# Filename: player_bench.py
# License: MIT License
# Author: Krusty/Benediction
# Date: 2025-11-11
# Version: 0.1
# Description: This file handles the conversion of music to a given replay format and the creation of snapshot and amsdos files


import enum
import re
import os
import subprocess
import logging
import platform
from utils import (
    execute_process,
    safe_getsize,
    safe_bndbuild_conversion,
    build_bndbuild_tokens,
)

from datasets import MusicFormat
import utils


class PlayerFormat(enum.Enum):
    FAP = "fap"
    AYT = "ayt"
    MINYQ = "minyq"
    AYC = "ayc"
    AKG = "akg"
    AKM = "akm"
    AKYS = "akys"
    AKYU = "akyu"
    CHPB = "chpb"

    """
    Returns the list of format that could produce it 
    """

    def requires_one_of(self):
        ym6_only = {MusicFormat.YM6}
        ym3_only = {MusicFormat.YM3}
        any_ym = {MusicFormat.YM3, MusicFormat.YM6}
        chp_only = {MusicFormat.CHP}

        at_compatible = {
            MusicFormat.AKS,
            MusicFormat.SKS,
            MusicFormat.ST,
            MusicFormat.VT2,
            MusicFormat.WYZ,
        }

        return {
            PlayerFormat.FAP: ym6_only,
            PlayerFormat.AYT: ym6_only,
            PlayerFormat.MINYQ: ym3_only,
            PlayerFormat.AYC: ym3_only,
            PlayerFormat.CHPB: chp_only,
            PlayerFormat.AKG: at_compatible,
            PlayerFormat.AKYS: at_compatible,
            PlayerFormat.AKYU: at_compatible,
            PlayerFormat.AKM: at_compatible.union(chp_only),
        }[self]

    @staticmethod
    def get_format(fname: str) -> "PlayerFormat":
        ext = fname.split(".")[-1].lower()
        for fmt in PlayerFormat:
            if fmt.value == ext:
                return fmt
        raise ValueError(f"Unsupported player format: {ext}")

    def set_extension(self, source: str) -> str:
        return os.path.splitext(source)[0] + "." + self.value

    def profiler_extra_size(self):
        """Return the number of bytes consumed by the extra profiling code

        Profiling code consists of:
        - 2 jp instructions at start (6 bytes)
        - profiler_init routine
        - profiler_run routine
        """
        profiler_header = 6  # 2 jp instructions (jp profiler_init, jp profiler_run)
        return {
            PlayerFormat.FAP: profiler_header + 19 + 15,  # 40 bytes total
            PlayerFormat.AYT: profiler_header + 22 + 9,  # 37 bytes (JP method)
            PlayerFormat.MINYQ: profiler_header
            + 12
            + 6,  # 24 bytes total (miniq profiler: ld hl,de,call + call)
            PlayerFormat.AYC: None,
            PlayerFormat.AKG: profiler_header
            + 12
            + 8,  # 26 bytes total (di+ld+xor+call+ei+jp + di+call+ei+jp)
            PlayerFormat.AKYS: profiler_header
            + 11
            + 8,  # 25 bytes total (jp 0xffff stubs)
            PlayerFormat.AKYU: profiler_header
            + 11
            + 8,  # 25 bytes total (jp 0xffff stubs)
            PlayerFormat.AKM: profiler_header
            + 9
            + 9,  # 24 bytes total (di+3 ld+call+ei+jp + di+call+ei+jp)
            PlayerFormat.CHPB: profiler_header
            + 3
            + 8,  # 17 bytes total (jp 0xffff + di+call+ei+jp)
        }[self]

    def load_address(self):
        return 0x500

    def is_stable(self) -> bool:
        """Return True if the player format has stable/constant CPU consumption."""
        return self in (PlayerFormat.AKYS, PlayerFormat.AYC, PlayerFormat.FAP)


def crunch_music_file(input_file: str, output_file: str, format: PlayerFormat) -> dict:
    return {
        PlayerFormat.FAP: crunch_ym_with_fap,
        PlayerFormat.AYT: crunch_ym_with_ayt,
        PlayerFormat.MINYQ: crunch_ym_with_minyq,
        PlayerFormat.AYC: crunch_ym_with_ayc,
        PlayerFormat.AKG: compile_aks_with_akg,
        PlayerFormat.AKYS: compile_aks_with_akys,
        PlayerFormat.AKYU: compile_aks_with_akyu,
        PlayerFormat.AKM: compile_aks_with_akm,
        PlayerFormat.CHPB: compile_chp,
    }[format](input_file, output_file)


def build_replay_program(data: dict, player: PlayerFormat) -> dict:
    (function, params) = {
        PlayerFormat.FAP: (build_replay_program_for_fap, ["buffer_size"]),
        PlayerFormat.AYT: (build_replay_program_for_ayt, []),
        PlayerFormat.MINYQ: (build_replay_program_for_minyq, ["buffer_size"]),
        PlayerFormat.AKG: (build_replay_program_for_akg, ["player_config"]),
        PlayerFormat.AKYS: (build_replay_program_for_akys, ["player_config"]),
        PlayerFormat.AKYU: (build_replay_program_for_akyu, ["player_config"]),
        PlayerFormat.AKM: (build_replay_program_for_akm, ["player_config"]),
        PlayerFormat.CHPB: (build_replay_program_for_chp, []),
    }[player]

    return function(data["compressed_fname"], player, **{k: data[k] for k in params})


def build_replay_program_for_chp(music_data_fname: str, player: PlayerFormat) -> dict:
    z80 = "players/chp/chp.asm"
    return __build_replay_program__(music_data_fname, "", z80, player)


def build_replay_program_for_ayt(music_data_fname: str, player: PlayerFormat) -> dict:
    # TODO get the number of nops returned by the builder
    #      ideally, it should be provided by the PC program
    z80 = "players/ayt/ayt.asm"
    return __build_replay_program__(music_data_fname, "-i ", z80, player)


def build_replay_program_for_akg(
    music_data_fname: str, player: PlayerFormat, player_config: str
) -> dict:
    z80 = "players/akg/akg.asm"
    return __build_replay_program__(
        music_data_fname, "", z80, player, config=player_config
    )


def build_replay_program_for_akys(
    music_data_fname: str, player: PlayerFormat, player_config: str
) -> dict:
    z80 = "players/akys/akys.asm"
    return __build_replay_program__(
        music_data_fname, "", z80, player, config=player_config
    )


def build_replay_program_for_akyu(
    music_data_fname: str, player: PlayerFormat, player_config: str
) -> dict:
    z80 = "players/akyu/akyu.asm"
    return __build_replay_program__(
        music_data_fname, "", z80, player, config=player_config
    )


def build_replay_program_for_akm(
    music_data_fname: str, player: PlayerFormat, player_config: str
) -> dict:
    z80 = "players/akm/akm.asm"
    return __build_replay_program__(music_data_fname, "", z80, player, player_config)


def build_replay_program_for_fap(
    music_data_fname: str, player: PlayerFormat, buffer_size: int
) -> dict:
    z80 = "players/fap/fap.asm"

    extra_cmd = (
        f'\\"-DFAP_INIT_PATH=\\\\\\"{{{{FAP_INIT_PATH|basm_escape_path}}}}\\\\\\"\\" '
        + f'\\"-DFAP_PLAY_PATH=\\\\\\"{{{{FAP_PLAY_PATH|basm_escape_path}}}}\\\\\\"\\" '
        + f'\\"-DMUSIC_BUFF_SIZE={buffer_size}\\" '
    )

    return __build_replay_program__(music_data_fname, extra_cmd, z80, player)


def build_replay_program_for_minyq(
    music_data_fname: str, player: PlayerFormat, buffer_size: int
) -> dict:
    """Build replay program for MinIQ/minyq players.

    Passes a `-DMUSIC_BUFF_SIZE` define to the assembler so the wrapper
    can reserve an appropriate cache/buffer size.
    """
    z80 = "players/miniq/miniq.asm"

    extra_cmd = f'\\"-DMUSIC_BUFF_SIZE={buffer_size}\\" '

    return __build_replay_program__(music_data_fname, extra_cmd, z80, player)


def __build_replay_program__(
    music_data_fname: str,
    extra_cmd: str,
    z80: str,
    player: PlayerFormat | None = None,
    config: str | None = None,
) -> dict:
    splits = os.path.splitext(music_data_fname)
    base = splits[0] + "_" + splits[1][1:]
    clean_amsdos_fname = base + ".BIN"
    sna_fname = base + ".sna"

    # Build basm command arguments
    basm_args = [
        "bndbuild",
        "--direct",
        "--with_expansion",
        "--",
        "basm",
    ]
    
    # Add extra_cmd tokens if provided (typically additional -D defines)
    if extra_cmd:
        # Split extra_cmd on spaces while preserving quoted strings
        import shlex
        basm_args.extend(shlex.split(extra_cmd))
    
    # Add standard defines
    basm_args.extend([
        f'-DMUSIC_DATA_FNAME=\\"{music_data_fname}\\"',
        f'-DMUSIC_EXEC_FNAME=\\"{clean_amsdos_fname}\\"',
    ])
    
    if config is not None:
        basm_args.append(f'-DPLAYER_CONFIG_FNAME=\\"{config}\\"')
    
    # Add snapshot output and source file
    basm_args.extend([
        "--snapshot",
        "-o",
        sna_fname,
        z80,
    ])
    
    tokens = build_bndbuild_tokens(*basm_args)
    execute_process(tokens)
    program_size = safe_getsize(clean_amsdos_fname)

    # Subtract profiling overhead if player format provided
    if player is not None:
        overhead = player.profiler_extra_size()
        if overhead is not None:
            program_size = max(0, program_size - overhead)

    zx0_fname = clean_amsdos_fname + ".zx0"
    tokens = build_bndbuild_tokens(
        "bndbuild",
        "--direct",
        "--",
        "compress",
        "--cruncher",
        "zx0",
        "--input",
        clean_amsdos_fname,
        "--output",
        zx0_fname,
    )
    execute_process(tokens)
    program_zx0_size = safe_getsize(zx0_fname)  # no header to remove

    return {
        "program_name": clean_amsdos_fname,
        "program_size": program_size,
        "program_zx0_size": program_zx0_size,
    }


def __crunch_or_compile_music__(src: str, tgt: str, cmd: str) -> dict:
    res = utils.execute_process(cmd)
    s = safe_getsize(tgt)
    return {
        "original_fname": src,
        "compressed_fname": tgt,
        "stdout": res.stdout.decode("utf-8"),
        "stderr": res.stderr.decode("utf-8"),
        "buffer_size": 0,
        "data_size": s,
        "play_time": -1,
    }


def crunch_ym_with_ayt(ym_fname: str, ayt_fname: str) -> dict:
    tokens = build_bndbuild_tokens(
        "bndbuild",
        "--direct",
        "--",
        "ayt",
        "--verbose",
        "--target",
        "CPC",
        ym_fname,
        "-o",
        ayt_fname,
    )

    res = __crunch_or_compile_music__(ym_fname, ayt_fname, tokens)
    res["data-size"] = safe_getsize(ayt_fname)
    return res


def crunch_ym_with_ayc(ym_fname: str, ayc_fname: str) -> dict:
    raise NotImplementedError("A pc cruncher is required")


def crunch_ym_with_minyq(ym_fname: str, miny_fname: str) -> dict:
    tokens = build_bndbuild_tokens(
        "bndbuild",
        "--direct",
        "--",
        "miny",
        "quick",
        ym_fname,
        miny_fname,
    )

    res = __crunch_or_compile_music__(ym_fname, miny_fname, tokens)

    # Ensure stdout is present
    stdout_text = res.get("stdout", "")
    # Look for lines like: "Total cache size:   1248"
    for line in stdout_text.splitlines():
        if "Total cache size" in line:
            m = re.search(r"(\d+)", line)
            if m:
                try:
                    res["buffer_size"] = int(m.group(1))
                except Exception:
                    res["buffer_size"] = -1

    return res


def compile_chp(chp_fname: str, _):
    assert ".CHP" in chp_fname
    chpz80_fname = chp_fname.replace(".CHP", ".CHPZ80")
    tokens1 = build_bndbuild_tokens(
        "bndbuild",
        "--direct",
        "--",
        "chipnsfx",
        chp_fname,
        chpz80_fname,
    )
    res = execute_process(tokens1)

    chpb_fname = chp_fname.replace(".CHP", ".CHPB")
    tokens2 = build_bndbuild_tokens(
        "bndbuild",
        "--direct",
        "--",
        "basm",
        chpz80_fname,
        "-o",
        chpb_fname,
    )
    res = execute_process(tokens2)

    s = safe_getsize(chpb_fname)

    return {
        "original_fname": chp_fname,
        "compressed_fname": chpz80_fname,
        "stdout": res.stdout.decode("utf-8"),
        "stderr": res.stderr.decode("utf-8"),
        "buffer_size": -1,  # TODO need to compute
        "data_size": s,
        "play_time": -1,
    }


def crunch_ym_with_fap(ym_fname: str, fap_fname: str) -> dict:
    cmd = ["bndbuild", "--direct", "--", "fap", "{in_path}", "{out_path}"]
    res_proc, stdout, stderr = safe_bndbuild_conversion(
        ym_fname, fap_fname, cmd, tmp_prefix="fap-"
    )

    s = safe_getsize(fap_fname)

    res = {
        "original_fname": ym_fname,
        "compressed_fname": fap_fname,
        "stdout": stdout,
        "stderr": stderr,
        "buffer_size": 0,
        "data_size": s,
        "play_time": -1,
    }

    for line in res["stdout"].splitlines():
        DECRUNCH_BUFF_SIZE = "Decrunch buffer size"
        PLAY_TIME = "Play time"

        if DECRUNCH_BUFF_SIZE in line:
            parts = line.split(":")[1]
            parts = parts.split("(")[0]
            parts = parts.strip()
            try:
                res["buffer_size"] = int(parts)
            except Exception:
                pass

        elif PLAY_TIME in line:
            time_parts = line.split(":")[1]
            time_parts = time_parts.split("N")[0]
            time_parts = time_parts.strip()
            try:
                res["play_time"] = int(time_parts)
            except Exception:
                pass
    return res


def rename_arkos_binary_for_fname_unicity(arkos_fname: str) -> str:
    base, ext = os.path.splitext(arkos_fname)
    return f"{base}_{ext[1:]}{ext}"


def __compile_aks_with_tool__(at_fname: str, output_fname: str, tool_name: str) -> dict:
    """
    Generic Arkos Tracker compilation helper for SongToAkg/Aky/Akm.

    Args:
        at_fname: Path to input AKS file
        output_fname: Path to output file (akg/akys/akm)
        tool_name: Tool name (Akg, Aky, or Akm)
    """
    tmp_fname = rename_arkos_binary_for_fname_unicity(output_fname)
    tokens = build_bndbuild_tokens(
        "bndbuild",
        "--direct",
        "--",
        f"SongTo{tool_name}",
        "-bin",
        "-adr",
        "0x506",
        "--exportPlayerConfig",
        at_fname,
        tmp_fname,
    )
    res = __crunch_or_compile_music__(at_fname, tmp_fname, tokens)
    res["compressed_fname"] = output_fname
    res["player_config"] = os.path.splitext(tmp_fname)[0] + "_playerconfig.asm"
    if os.path.exists(output_fname):
        os.remove(output_fname)
    os.rename(tmp_fname, output_fname)
    return res


def compile_aks_with_akg(at_fname, akg_fname):
    return __compile_aks_with_tool__(at_fname, akg_fname, "Akg")


def compile_aks_with_akys(at_fname, akys_fname):
    return __compile_aks_with_tool__(at_fname, akys_fname, "Aky")


def compile_aks_with_akyu(at_fname, akyu_fname):
    return __compile_aks_with_tool__(at_fname, akyu_fname, "Aky")


def compile_aks_with_akm(at_fname, akm_fname):
    return __compile_aks_with_tool__(at_fname, akm_fname, "Akm")
