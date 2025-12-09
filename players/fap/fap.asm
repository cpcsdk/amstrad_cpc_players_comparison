    ORG	#500      

	; START Specific code for the profiler ; should not count
	jp profiler_init
	jp profiler_run
	; STOP Specific code for the profiler

    RUN	$
    ;
    ; You known the story ;)
    ;
    ld	hl, #C9FB
    ld	(#38), hl
    ld sp, $

		ld bc, 0xbc00+1 : out (c), c
		ld bc, 0xbd00+0 : out (c), c
    ;
    ; Initialize the player.
    ; Once the player is initialized, you can overwrite the init code if you need some extra memory.
    ;
    ld	a, hi(FapBuff)	; High byte of the decrunch buffer address.
    ld	bc, FapPlay     ; Address of the player binary.
    ld	de, ReturnAddr  ; Address to jump after playing a song frame.
    ld	hl, FapData     ; Address of song data.
    di
    call    FapInit
    ei
    
    ;
    ; Main loop
    ;
MainLoop:
    ld	b, #F5
    in	a, (c)
    rra
    jr	nc, MainLoop

    halt		; Wait to make sure the VBL is over.
    halt
    
    di			; Prevent interrupt apocalypse
    ld	(RestoreSp), sp	; Save our precious stack-pointer

    		ld bc,#7f10		; Border 
		ld a,#4c
		out (c),c		; select border
		out (c),a		; in red

    jp	FapPlay		; Jump into the replay-routine

ReturnAddr:		; Return address the replay-routine will jump back to

RestoreSp = $+1
    ld	sp, 0		; Restore our precious stack-pointer

		ld bc,#7f54
		out (c),c

    ei			; We may enable the maskable interrupts again



    jp	MainLoop

    ;
    ; Load files
    ;
    FapInit: incbin FAP_INIT_PATH
    FapPlay: incbin FAP_PLAY_PATH
    FapData: incbin MUSIC_DATA_FNAME
    align 256
    FapBuff: defs MUSIC_BUFF_SIZE

	; START Specific code for the profiler ; should not count
profiler_init
	ld	a, hi(FapBuff)	; High byte of the decrunch buffer address.
	ld	bc, FapPlay     ; Address of the player binary.
	ld	de, profiler_return_addr  ; Address to jump after playing a song frame.
	ld	hl, FapData     ; Address of song data.
	di
	call    FapInit
	ei
	jp 0xffff
profiler_run
	di
	ld	(profiler_restore_sp), sp	; Save our precious stack-pointer
	jp	FapPlay		; Jump into the replay-routine
profiler_return_addr
profiler_restore_sp = $+1
	ld	sp, 0		; Restore our precious stack-pointer
	ei
	jp 0xffff
	; STOP specific code for the profiler

    save MUSIC_EXEC_FNAME