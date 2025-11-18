#!/usr/bin/env python3
# -*- coding: utf-8 -*-


# Filename: player_bench.py
# License: MIT License
# Author: Krusty/Benediction
# Date: 2025-11-11
# Version: 0.1
# Description: This file handles the conversion of music to a given replay format and the creation of snapshot and amsdos files


import enum
import os
import subprocess
import logging
import platform

from datasets import MusicFormat
import utils

class PlayerFormat(enum.Enum):
    FAP = "fap"
    AYT = "ayt"
    MINY = "miny"
    AYC = "ayc"
    AKG = "akg" 
    AKM = "akm"
    AKY = "aky"
    CHP = "chpdb"

    """
    Returns the list of format that could produce it 
    """
    def requires_one_of(self):
        ym_only = {MusicFormat.YM6}
        chp_only = {MusicFormat.CHP}

        at_compatible = {MusicFormat.AKS, MusicFormat.SKS, MusicFormat.ST, MusicFormat.VT2, MusicFormat.WYZ}
        
        return {
            PlayerFormat.FAP: ym_only,
            PlayerFormat.AYT: ym_only,
            PlayerFormat.MINY: ym_only,
            PlayerFormat.AYC: ym_only,

            PlayerFormat.CHP: chp_only,

            PlayerFormat.AKG: at_compatible,
            PlayerFormat.AKY: at_compatible,

            PlayerFormat.AKM: at_compatible.union(chp_only),
        }[self]

    def get_format(fname: str) -> 'PlayerFormat':
        ext = fname.split('.')[-1].lower()
        for fmt in PlayerFormat:
            if fmt.value == ext:
                return fmt
        raise ValueError(f"Unsupported player format: {ext}")


def crunch_music_file(input_file: str, format: PlayerFormat) :
    return {
        PlayerFormat.FAP: crunch_ym_with_fap,
        PlayerFormat.AYT: crunch_ym_with_ayt,
        PlayerFormat.MINY: crunch_ym_with_miny,
        PlayerFormat.AYC: crunch_ym_with_ayc,
        PlayerFormat.AKG: compile_aks_with_akg,
        PlayerFormat.AKY: compile_aks_with_aky,
        PlayerFormat.AKM: compile_aks_with_akm,
        PlayerFormat.CHP: compile_chp,
    }[format](input_file)

def build_replay_program(data, player: PlayerFormat):
    (function, params)  = {
        PlayerFormat.FAP: (
            build_replay_program_for_fap,
            ["buffer_size"]
        ),

        PlayerFormat.AYT: (
            build_replay_program_for_ayt,
            []
        ),

        PlayerFormat.AKY: (
            build_replay_program_for_aky,
            []
        ),

        PlayerFormat.AKM: (
            build_replay_program_for_aky,
            []
        ),

        PlayerFormat.CHP: (
            build_replay_program_for_chp,
            []
        )
    }[player]
    

    return function(data["compressed_fname"], **{k: data[k] for k in params})


def build_replay_program_for_chp(music_data_fname):
    z80 = "players/chp/chp.asm"
    return __build_replay_program__(music_data_fname, "", z80)

def build_replay_program_for_ayt(music_data_fname):
    # TODO get the number of nops returned by the builder
    #      ideally, it should be provided by the PC program
    z80 = "players/ayt/ayt.asm"
    return __build_replay_program__(music_data_fname, "-i ", z80)

def build_replay_program_for_aky(music_data_fname):
    z80 = "players/aky/aky.asm"
    return __build_replay_program__(music_data_fname, "", z80)

def build_replay_program_for_akm(music_data_fname):
    z80 = "players/akm/akm.asm"
    return __build_replay_program__(music_data_fname, "", z80)

def build_replay_program_for_fap(music_data_fname, buffer_size):
    z80 = "players/fap/fap.asm"
    
    extra_cmd = f"\\\"-DFAP_INIT_PATH=\\\\\\\"{{{{FAP_INIT_PATH|basm_escape_path}}}}\\\\\\\"\\\" " \
    + f"\\\"-DFAP_PLAY_PATH=\\\\\\\"{{{{FAP_PLAY_PATH|basm_escape_path}}}}\\\\\\\"\\\" " \
    + f"\\\"-DMUSIC_BUFF_SIZE={buffer_size}\\\" "

    return __build_replay_program__(music_data_fname, extra_cmd, z80)

def __build_replay_program__(music_data_fname, extra_cmd, z80):
    splits = os.path.splitext(music_data_fname)
    base = splits[0] + "_" + splits[1][1:]
    amsdos_fname = base + ".BIN"
    sna_fname =  base + ".sna"

    if  "Windows" in platform.system():
        rep = r"\\\\"
        amsdos_fname = amsdos_fname.replace("\\", rep)
        music_data_fname = music_data_fname.replace("\\", rep)
        sna_fname = sna_fname.replace("\\", rep)

    cmd = f"bndbuild --direct --with_expansion -- basm " + extra_cmd + " " \
    + f"\\\"-DMUSIC_DATA_FNAME=\\\\\\\"{music_data_fname}\\\\\\\"\\\"  " \
    + f"\\\"-DMUSIC_EXEC_FNAME=\\\\\\\"{amsdos_fname}\\\\\\\"\\\" " \
    + f"--snapshot " \
    + f"-o \\\"{sna_fname}\\\" \\\"{z80}\\\" "

    print(cmd)
    subprocess.run(cmd, check=True)
    return {
        "program_size": os.path.getsize(amsdos_fname) - 128
    }




def __crunch_or_compile_music__(src, tgt, cmd):
    res = utils.execute_process(cmd)

    try:
        s = os.path.getsize(tgt)
    except :
        s = -1
    return {
        'original_fname': src,
        'compressed_fname': tgt,
        'stdout': res.stdout.decode('utf-8'),
        'stderr': res.stderr.decode('utf-8'),
        'buffer_size': 0,
        'data_size': s,
        'play_time': -1
    }

def crunch_ym_with_ayt(ym_fname: str):
    ayt_fname = ym_fname.replace(".ym", ".ayt")
    cmd_line = f"bndbuild --direct -- ayt --verbose --target CPC \\\"{ym_fname}\\\"" # \\\"{fap_fname}\\\""
    res = __crunch_or_compile_music__(ym_fname, ayt_fname, cmd_line)

    #fix missing -o --output
    if os.path.exists(ayt_fname):
        os.remove(ayt_fname)
    os.rename(os.path.basename(ayt_fname), ayt_fname)
    res['data-size'] =  os.path.getsize(ayt_fname)
    return res

def crunch_ym_with_ayc(ym_fname: str):
    raise NotImplementedError("A pc cruncher is required")

def crunch_ym_with_miny(ym_fname: str):
    raise NotImplementedError("Waiting the newest version compatible with YM6")

def compile_chp(chp_fname: str):
    assert ".CHP" in chp_fname
    chpz80_fname = chp_fname.replace(".CHP", ".CHPZ80")
    cmd_line = f"bndbuild --direct -- chipnsfx \\\"{chp_fname}\\\" \\\"{chpz80_fname}\\\""  
    res = utils.execute_process(cmd_line)

    chpb_fname = chp_fname.replace(".CHP", ".CHPB")
    cmd_line = f"bndbuild --direct -- basm \\\"{chpz80_fname}\\\" -o \\\"{chpb_fname}\\\""  
    res = utils.execute_process(cmd_line)

    try:
        s = os.path.getsize(chpb_fname)
    except :
        s = -1

    return {
        'original_fname': chp_fname,
        'compressed_fname': chpz80_fname,
        'stdout': res.stdout.decode('utf-8'),
        'stderr': res.stderr.decode('utf-8'),
        'buffer_size': -1, # TODO need to compute
        'data_size': s,
        'play_time': -1
    }

def crunch_ym_with_fap(ym_fname: str):
    fap_fname = ym_fname.replace(".ym", ".fap")
    cmd_line = f"bndbuild --direct -- fap \\\"{ym_fname}\\\" \\\"{fap_fname}\\\""
    res = __crunch_or_compile_music__(ym_fname, fap_fname, cmd_line)
    for line in res["stdout"].splitlines():
        DECRUNCH_BUFF_SIZE="Decrunch buffer size"
        PLAY_TIME="Play time"

        if DECRUNCH_BUFF_SIZE in line:
            line = line.split(":")[1]
            line:str = line.split("(")[0]
            line = line.strip()
            res["buffer_size"] = int(line)

        elif PLAY_TIME in line:
            line = line.split(':')[1]
            line = line.split('N')[0]
            line = line.strip()
            res["play_time"] = int(line)
    return res

def compile_aks_with_akg(at_fname):
    akg_fname = os.path.splitext(at_fname)[0] + ".akg"
    cmd_line = f"bndbuild --direct -- SongToAkg -bin -adr 0x500 \\\"{at_fname}\\\" \\\"{akg_fname}\\\" "
    return __crunch_or_compile_music__(at_fname, akg_fname, cmd_line)

def compile_aks_with_aky(at_fname):
    aky_fname = os.path.splitext(at_fname)[0] + ".aky"
    cmd_line = f"bndbuild --direct -- SongToAky -bin -adr 0x500 \\\"{at_fname}\\\" \\\"{aky_fname}\\\" "
    return __crunch_or_compile_music__(at_fname, aky_fname, cmd_line)


def compile_aks_with_akm(at_fname):
    akm_fname = os.path.splitext(at_fname)[0] + ".akm"
    cmd_line = f"bndbuild --direct -- SongToAkm -bin -adr 0x500 \\\"{at_fname}\\\" \\\"{akm_fname}\\\" "
    return __crunch_or_compile_music__(at_fname, akm_fname, cmd_line)

