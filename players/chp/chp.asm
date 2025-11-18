
    org 0x500

CHIPNSFX_FLAG=4+256

MyProgram
CHP_File
		include MUSIC_DATA_FNAME

chip_song_a equ song_a
chip_song_b equ song_b
chip_song_c equ song_c

chipnsfx
    include "CHIPNSFX.I80"

		run $
        BREAPOINT
StartExample
		ld sp,MyProgram
		ld hl,#c9fb		; Cpc interrupt reduced to ei/ret
		ld (#38),hl		;


		ld bc, 0xbc00+1 : out (c), c
		ld bc, 0xbd00+0 : out (c), c

        di
      ;  ld hl, song_header : xor a
      ;  call chip_song
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
		call chip_play		; call method for the player. 
        ei
		;-------------------------------------------------------------------------------------------------------------------------------
		; Black Color Border
		;-------------------------------------------------------------------------------------------------------------------------------
		ld bc,#7f54
		out (c),c

		jr MainLoop


writepsg: ; A=VALUE,C=INDEX; -
		PUSH BC
		LD B,$F4
		OUT (C),C
		LD BC,$F6C0
		OUT (C),C
		DW $71ED ; *OUT (C),0
		LD B,$F4
		OUT (C),A
		LD BC,$F680
		OUT (C),C
		DW $71ED ; *OUT (C),0
		POP BC
		RET

song_header:
    DEFW song_a-$-2
    DEFW song_b-$-2
    DEFW song_c-$-2




    save MUSIC_EXEC_FNAME

		

