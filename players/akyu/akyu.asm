    org 0x500

PLY_AKY_REMOVE_HOOKS = 1
PLY_AKY_HARDWARE_CPC = 1

	include PLAYER_CONFIG_FNAME

	; START Specific code for the profiler ; should not count
	jp profiler_init
	jp profiler_run
	; STOP Specific code for the profiler

AKYU_File
		assert $ == 0x506
		incbin MUSIC_DATA_FNAME

	include "PlayerAky.asm"
		run $
        BREAPOINT
StartExample
		ld sp, 0x500
		ld hl,#c9fb		; Cpc interrupt reduced to ei/ret
		ld (#38),hl		;


		ld bc, 0xbc00+1 : out (c), c
		ld bc, 0xbd00+0 : out (c), c

        di
        xor a
        ld hl, AKYU_File
        call PLY_AKY_Init
        ei
MainLoop	
		ld b,#f5		; ppi port b
WaitVsync		
		in a,(c)		; Wait Vsync
		rra
		jr nc,WaitVsync
		;
		halt			; some delay
		halt

		;-------------------------------------------------------------------------------------------------------------------------------
		; Red Color Border
		;-------------------------------------------------------------------------------------------------------------------------------
		ld bc,#7f10		; Border 
		ld a,#4c
		out (c),c		; select border
		out (c),a		; in red
		;
		;-------------------------------------------------------------------------------------------------------------------------------
		di
		call PLY_AKY_Play		; call method for the player (unstable version).
        ei
		;-------------------------------------------------------------------------------------------------------------------------------
		; Blue Color Border
		;-------------------------------------------------------------------------------------------------------------------------------
		ld bc,#7f10
		ld a,#44
		out (c),c		; select border
		out (c),a		; in blue
		;
		;-------------------------------------------------------------------------------------------------------------------------------

		jr MainLoop


; ==============================================================================
; Profiler init (called at startup, we use this to prepare the profiler)
; ==============================================================================
profiler_init:
	di
	xor a
	ld hl, AKYU_File
	call PLY_AKY_Init
	ei
	jp 0xffff

; ==============================================================================
; Profiler run (called each frame in the loop)
; ==============================================================================
profiler_run:
	di
	call PLY_AKY_Play
	ei
    jp 0xffff

	; Persist assembled binary for benchmarking
	save MUSIC_EXEC_FNAME
