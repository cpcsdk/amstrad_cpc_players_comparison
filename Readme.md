# Player benchmark for Amstrad CPC

## Aim

The aim of this repository is to benchmark state-of-the-art music players on Amstrad CPC.

For a given dataset, the music are converted with various replay formats.
An executable is build for each of these formats.
The length of the executable is then retreived to be compared with the other players.

Why using the lenght of this executable and not player and music file ?

 - All extra boilerplate is common with all players, so it does not count in the comparison. We can still substract it.
 - Some players require a buffer. This has to be taken into account with the size.
 - Some players require a save of the stack pointer. This mechanism has to be taken into account, we can consider it takes part of the player routine.
 - Some players require code generation. Even if this code can be removed after usage, this has to be taken into account.

The duration will be collected in future versions. Only FAP allows to retrieve it automatically and easily at the moment.

## Current bugs

 - There is a bug in the execution program for AKY and AKM. The sound is incorrect. This has to be investigated
 - The current ArkosTracker benchmark does not convert formats different than AKS because of some bug somewhere. This has to be fixed to increase dataset size.


## Current limitations

 - This is currently a one man project, the project will be unbiased and finished if other persons join to finish it
 - There is no cache handling => all files are converted/built at each run. It is mandatory to check their existence and not regenerate them !
 - This version has been tested on Windows only. It fails on Linux ATM
 - Player duration has not been taken into account yet. This is mandatory to collect this metric. The choice of the player has to be done on the paret front of a 2d scatter plot on size vs time
 - If have not checked the memory impact of players with code generation. This will be mandatory to adjust figures based on that
 - There is only a single dataset. Various with various properties are expected.
 - AYC cruncher is missing. Either it requires a dedicated PC program (but I have not found a modern one), either it requires emulation with CSL scripting (I have not checked the feasability of the thing)
 - AKM player is used even on music not compatible because they use fancy effects. 
 - FAP does not correct frequency, but AYT does. I do not know if it can be unfair

## Usage

To launch the current benchmark:

```bash
python player_bench.py
```

Additional configurations and options will be added later, depending on community participation.

## Dependencies

The python script uses the following dependencies: `matplotlib`, `seaborn`, `pandas`, `tabulate`.
It also requires the `bndbuild` tool which control the various crunchers.


## Datasets evaluation

### ArkosTracker3 AKS dataset
#### Program size

|    | sources                                    |   .akm |   .aky |   .ayt |   .fap |
|---:|:-------------------------------------------|-------:|-------:|-------:|-------:|
|  0 | 2018_EA_demosong                           |   2380 |   4088 |   6088 |   6338 |
|  1 | 2018_nq_skrju_demosong                     |   3996 |   6212 |   7827 |   8130 |
|  2 | Andy Severn - Lop Ears                     |   1823 |   4017 |   6590 |   8642 |
|  3 | Doclands - Buzz-o-Meter (YM)               |   5540 |   9395 |  20081 |   9410 |
|  4 | Doclands - Pong Cracktro (YM)              |   7451 |  11517 |  19285 |  11970 |
|  5 | Doclands - Slowly But (YM)                 |   4788 |   8005 |  12007 |   7362 |
|  6 | Doclands - The Rivals (YM)                 |   5895 |  11671 |  18547 |   9410 |
|  7 | Doclands - The Saga (YM)                   |   5314 |   9081 |  15515 |   8386 |
|  8 | Doclands - Tiny Things (YM)                |   4866 |   8917 |  16125 |  10690 |
|  9 | Doclands - Truly Yours (YM)                |   5955 |  11791 |  16527 |  10434 |
| 10 | Doclands - Your Credits (YM)               |   3690 |   5755 |   9890 |   8642 |
| 11 | Excellence in Art 2018 - Just add cream    |   3872 |   8475 |  18577 |  17090 |
| 12 | FenyxKell - BD10n'nOeuf                    |   2789 |  10173 |  12117 |  10946 |
| 13 | FenyxKell - Bobline                        |   2487 |   6076 |  10515 |   7874 |
| 14 | FenyxKell - KellyOn                        |   5147 |  10202 |  13966 |   9922 |
| 15 | FenyxKell - Smoke                          |   1888 |   2754 |   3687 |   4802 |
| 16 | FenyxKell - Solarium                       |   2519 |   3578 |   6316 |   6082 |
| 17 | FenyxKell - Spectrum Castle                |   3944 |  15636 |  25327 |  13250 |
| 18 | Giherem - Bancaloide                       |   2592 |   5220 |  10524 |   6850 |
| 19 | Playing with effects                       |   1743 |   6245 |   9580 |   6594 |
| 20 | PulkoMandy - Renegade Remix                |   4139 |  11412 |  44005 |  16322 |
| 21 | SoundEffects                               |   1501 |   1605 |   1517 |   4290 |
| 22 | Targhan - A Harmless Grenade               |   2334 |   4832 |   8871 |   6850 |
| 23 | Targhan - Crtc                             |   7490 |  19261 |  40287 |  19906 |
| 24 | Targhan - Crtc - End part                  |   2729 |   8974 |  11366 |   8898 |
| 25 | Targhan - Dead On Time - Ingame            |   3028 |   6973 |   9428 |   7106 |
| 26 | Targhan - Dead On Time - Main Menu         |   2673 |   5472 |   8871 |   6594 |
| 27 | Targhan - Dead On Time - Sound Effects     |   1718 |   1906 |   2990 |   4802 |
| 28 | Targhan - DemoIzArt - End Part             |   9727 |  29436 |  49918 |  26050 |
| 29 | Targhan - DemoIzArt - Twist Part           |   7059 |  17345 |  27492 |  16578 |
| 30 | Targhan - Hocus Pocus                      |   5709 |  16438 |  26206 |  15560 |
| 31 | Targhan - Midline Process - Carpet         |   8272 |  17982 |  39392 |  20674 |
| 32 | Targhan - Midline Process - Molusk         |   8453 |  23980 |  47479 |  30402 |
| 33 | Targhan - Ooops                            |   1685 |   2499 |   4597 |   5314 |
| 34 | Targhan - Orion Prime - Danger Ahead       |   1581 |   2276 |   2710 |   4546 |
| 35 | Targhan - Orion Prime - Fight              |   1697 |   2665 |   4409 |   5058 |
| 36 | Targhan - Orion Prime - Introduction       |   5683 |  22856 |  33282 |  14786 |
| 37 | Targhan - Orion Prime - Level 1            |   3164 |   8701 |  24782 |  10952 |
| 38 | Targhan - Orion Prime - Level 4 - Theme 1  |   3042 |   7028 |  26365 |  10946 |
| 39 | Targhan - Orion Prime - Level 4 - Theme 2  |   3322 |  16233 |  25456 |  14018 |
| 40 | Targhan - Star Sabre - Boss Theme          |   2124 |   3861 |   5111 |   5570 |
| 41 | Targhan - Star Sabre - Ingame              |   3668 |   9697 |  16928 |   9922 |
| 42 | Targhan - Star Sabre - Intermission        |   2516 |   6222 |  10784 |   7874 |
| 43 | Targhan - Star Sabre - Main Menu           |   3347 |   9537 |  17842 |  10178 |
| 44 | Targhan - Wunderbar                        |   2102 |   3964 |  10845 |   6850 |
| 45 | Tom&Jerry - Boules Et Bits (Extended)      |   4112 |   8404 |  19816 |  16066 |
| 46 | Tom&Jerry - From Scratch - Part 1          |   3095 |   5937 |  10856 |   6338 |
| 47 | Tom&Jerry - From Scratch - Part 2          |   2486 |   3928 |  10250 |   8642 |
| 48 | Tom&Jerry - From Scratch - Part 3          |   2845 |   5038 |   7496 |   7618 |
| 49 | Tom&Jerry - From Scratch - Part 4          |   2827 |   4541 |  10520 |   7362 |
| 50 | Tom&Jerry - Le Crime Du Parking - End Game |   1900 |   3332 |   5463 |   5570 |
| 51 | Tom&Jerry - Le Crime Du Parking - Intro    |   2969 |   8745 |  19015 |  13250 |
| 52 | Tom&Jerry - Sudoku - Menu                  |   1788 |   3070 |   4409 |   5058 |
| 53 | Tom&Jerry - Sudoku - Notice                |   1613 |   2519 |   4709 |   5058 |
| 54 | Tom&Jerry - Sudoku - Sundat                |   1808 |   4113 |   4437 |   5058 |
| 55 | Tom&Jerry - Sudoku - Theme 1               |   4271 |   8928 |  31471 |  20162 |
| 56 | Tom&Jerry - Sudoku - Theme 2               |   3928 |  11781 |  25230 |  10952 |
| 57 | Tom&Jerry - Sudoku - Victory               |   1807 |   2992 |   3584 |   5058 |
| 58 | Totta - BaraBadaBastu                      |   2498 |   4505 |   7304 |   7624 |
| 59 | Totta - Crawlers                           |   5237 |   9877 |  13622 |   9928 |
| 60 | Totta - Hardy                              |  10485 |  21289 |  32639 |  18376 |
| 61 | Totta - Mellow                             |   5326 |  12798 |  21977 |  14530 |
| 62 | Totta - Rezzy                              |   6795 |  13330 |  19803 |  12226 |
| 63 | Totta - Room5                              |   3329 |   9190 |   9863 |  10690 |
| 64 | UltraSyd - Dead Floppy                     |   2507 |   4767 |  14134 |  11970 |
| 65 | UltraSyd - Fractal                         |   5349 |   8177 |  19171 |  15298 |
| 66 | UltraSyd - Fuck It                         |   6028 |  11425 |  23873 |  14792 |
| 67 | UltraSyd - Robot                           |   5545 |  12299 |  28495 |  18370 |
| 68 | UltraSyd - The End                         |   6526 |  14277 |  30260 |  22722 |
| 69 | UltraSyd - YM Type                         |   3857 |  12193 |  23759 |  16584 |
| 70 | Ultrasyd - Morons                          |   7419 |  13703 |  41341 |  20930 |
| 71 | jinj_med                                   |   1519 |   1985 |   3258 |   5058 |
| 72 | maryjane2                                  |   2917 |   4882 |   9225 |   7106 |