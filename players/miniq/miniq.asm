

; Program load address for builder/emulator runs
Loading		equ #500

        org Loading

		jp profiler_init
		jp profiler_run

		assert $ == 0x506
MINIQ_FILE
		incbin MUSIC_DATA_FNAME


		read "ymp_z80.z80"

StartExample
		run $
		BREAKPOINT
        ld sp, 0x500
		ld hl,#c9fb		; Cpc interrupt reduced to ei/ret
		ld (#38),hl		;

        ; Initialize player
		di
        ld hl, MINIQ_FILE; hl = pointer to packed YMP tune (incbin)
        ld de, player_cache; de = pointer to writable player cache
        call ymp_player_init
		ei
MainLoop
        ; Wait VSync (simple busy wait using port C, mirrors other examples)
        in a,(c)
        rra
        jr nc,MainLoop

		halt : halt

		ld bc,#7f10		; Border 
		ld a,#4c
		out (c),c		; select border
		out (c),a		; in red

        ; Call the YMP player update routine (produce next frame)
		di
		call ymp_player_update
		ei

		ld bc,#7f54
		out (c),c

        jp MainLoop

; ---------------------------------------------------------------------
; Data / buffers
; ---------------------------------------------------------------------
player_state
	ds ymp_size,#00
player_state_end equ $
; ---------------------------
; LZ cache for player. Size depends on the compressed file.
; ---------------------------
player_cache
	ds	MUSIC_BUFF_SIZE,#00		; (or whatever size you need); TODO use information provided by the player
player_cache_end equ $


; profiler entrypoints (used by test runner / profiler harness)
profiler_init
        ld hl,MINIQ_FILE
        ld de, player_cache
        call ymp_player_init
        jp 0xffff

profiler_run
        call ymp_player_update
        jp 0xffff

; tell the build tool to save output binary under expected name
        save MUSIC_EXEC_FNAME
