    org 0x500
AKY_File
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
        ld hl, AKY_File
        call PLY_AKYst_Init
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
		call PLY_AKYst_Play		; call method for the player. 
        ei
		;-------------------------------------------------------------------------------------------------------------------------------
		; Black Color Border
		;-------------------------------------------------------------------------------------------------------------------------------
		ld bc,#7f54
		out (c),c

		jr MainLoop

 include "PlayerAkyStabilized_CPC.asm"


    save MUSIC_EXEC_FNAME

		

