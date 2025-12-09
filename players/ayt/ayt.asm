;;**********************************************************************************************************************************************
;; AMSTRAD CPC 
;;**********************************************************************************************************************************************
;;
;; AYT EXAMPLE / SAMPLE
;;
;;**********************************************************************************************************************************************
;;----------------------------------------------------------------------------------------------------------------------------------------------
AYT_Player	equ #100		; Address for player created by builder (247 to 317 bytes according AYT file & Player settings) 
					; + 57 bytes of AY Init routine when there are less than 14 registers in AYT files.
;AYT_File	equ #1000		; Address of AYT file in memory
MyStack equ AYT_Player

Loading	equ #500
;;----------------------------------------------------------------------------------------------------------------------------------------------
;;============================================================================================================================================
		org Loading
		; START Specific code for the profiler ; should not count
		jp profiler_init
		jp profiler_run
		; STOP Specific code for the profiler
	
AYT_Builder

		
		read "AytPlayerBuilder-CPC.asm"
;;============================================================================================================================================
MyProgram		
		run $
        BREAPOINT
StartExample
		ld sp,MyStack
		ld hl,#c9fb		; Cpc interrupt reduced to ei/ret
		ld (#38),hl		;


		ld bc, 0xbc00+1 : out (c), c
		ld bc, 0xbd00+0 : out (c), c

					; int active
		;-------------------------------------------------------------------------------------------------------------------------------
		; Build the player routine (needs 247 to 317 bytes, and 57 bytes more if less than 14 regs in AYT file)
		; Note that these 57 bytes can be retrieved after the first call to the player. 
		;-------------------------------------------------------------------------------------------------------------------------------
		ld ix,AYT_File		; Ptr on AYT_File
		ld de,AYT_Player	; Ptr of Adress where Player is built
		ld a,1			; Nb of loop for the music
    if PlayerAccessByJP			; Builder option for JP Method needs the address return of player.
		ld hl,AYT_Player_Ret	; Ptr where player come back in MyProgram
    endif
		call AYT_Builder	; Build the player at <de> for file pointed by <ix> for <a> loop
		;-------------------------------------------------------------------------------------------------------------------------------
		; Manages actions related to compilation options
		;-------------------------------------------------------------------------------------------------------------------------------
    if PlayerAccessByJP			; If JP Method is on, you may need to save SP
		ld (AYT_Player_ReloadSP),sp ; Save current Stack Pointer 
    endif
		;-------------------------------------------------------------------------------------------------------------------------------
		ei			; Builder do a "di" (You can leave interruptions if necessary)
		;
		;-------------------------------------------------------------------------------------------------------------------------------
		; Main Code Playing Music
		;-------------------------------------------------------------------------------------------------------------------------------
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
		;; Calling player (JP or CALL method)
		;; Note that:
		;; - At the first call to the player, when the AYT file contains fewer than 14 registers, the constant AY registers are initialized, 
		;;   respecting the constant duration of the player for subsequent calls.
		;; - When the music loops (at its starting point or at the point set in the original YM), the duration remains constant.
		;; - When the music ends, the sound is stopped, and the routine continues to play a constant duration.
		;-------------------------------------------------------------------------------------------------------------------------------
		;
    if PlayerAccessByJP
		jp AYT_Player		; jump to the player
AYT_Player_Ret				; address return of the player	
AYT_Player_ReloadSP equ $+1
		ld sp,0			
    else
		call AYT_Player		; call method for the player. 
    endif
		;-------------------------------------------------------------------------------------------------------------------------------
		; Black Color Border
		;-------------------------------------------------------------------------------------------------------------------------------
		ld bc,#7f54
		out (c),c

		jr MainLoop

;;============================================================================================================================================
;;**********************************************************************************************************************************************
;; FILE AYT 
;;**********************************************************************************************************************************************
AYT_File
		incbin MUSIC_DATA_FNAME

	; START Specific code for the profiler ; should not count
profiler_init
	ld ix,AYT_File		; Ptr on AYT_File
	ld de,AYT_Player	; Ptr of Adress where Player is built
	ld a,1			; Nb of loop for the music
    if PlayerAccessByJP
		ld hl,profiler_run_return	; Ptr where player come back
    endif
	call AYT_Builder	; Build the player
    if PlayerAccessByJP
		ld (profiler_run_ReloadSP),sp ; Save current Stack Pointer 
    endif
	jp 0xffff
profiler_run
    if PlayerAccessByJP
	jp AYT_Player		; jump to the player
profiler_run_return
profiler_run_ReloadSP equ $+1
	ld sp,0			
    else
	call AYT_Player		; call method for the player. 
    endif
	jp 0xffff
	; STOP specific code for the profiler

    save MUSIC_EXEC_FNAME

		

