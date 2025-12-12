    org 0x500

	include PLAYER_CONFIG_FNAME

	; START Specific code for the profiler ; should not count
	jp profiler_init
	jp profiler_run
	; STOP Specific code for the profiler

PLY_AKG_REMOVE_HOOKS
PLY_AKG_HARDWARE_CPC = 1
AKG_File
	assert $ == 0x506
	incbin MUSIC_DATA_FNAME

	run $
        BREAPOINT
StartExample
	ld sp, 0x500
	ld hl,#c9fb		; Cpc interrupt reduced to ei/ret
	ld (#38),hl		;


	ld bc, 0xbc00+1 : out (c), c
	ld bc, 0xbd00+0 : out (c), c

        di
        ld hl, AKG_File
        xor a
        call PLY_AKG_Init
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
	call PLY_AKG_Play		; call method for the player. 
        ei
	;-------------------------------------------------------------------------------------------------------------------------------
	; Black Color Border
	;-------------------------------------------------------------------------------------------------------------------------------
	ld bc,#7f54
	out (c),c

	jr MainLoop

 include "PlayerAkg.asm"

	; START Specific code for the profiler ; should not count
profiler_init
	di
	ld hl, AKG_File
	xor a
	call PLY_AKG_Init
	ei
	jp 0xffff
profiler_run
	di
	call PLY_AKG_Play		; call method for the player. 
	ei
	jp 0xffff
	; STOP specific code for the profiler

    save MUSIC_EXEC_FNAME
