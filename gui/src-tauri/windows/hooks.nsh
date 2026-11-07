; Explorer "Sproutで開く" for folders and folder backgrounds.
; The installer is per-user, so the entries live in HKCU and need no administrator rights.
; Kept in UTF-8 with BOM so NSIS reads the Japanese menu text correctly.

!define SPROUT_FOLDER_VERB "Software\Classes\Directory\shell\OpenWithSprout"
!define SPROUT_BACKGROUND_VERB "Software\Classes\Directory\Background\shell\OpenWithSprout"

!macro SPROUT_WRITE_VERB KEY
  WriteRegStr HKCU "${KEY}" "MUIVerb" "Sproutで開く"
  WriteRegStr HKCU "${KEY}" "Icon" "$\"$INSTDIR\${MAINBINARYNAME}.exe$\",0"
  WriteRegStr HKCU "${KEY}\command" "" "$\"$INSTDIR\${MAINBINARYNAME}.exe$\" $\"%V$\""
!macroend

!macro NSIS_HOOK_POSTINSTALL
  !insertmacro SPROUT_WRITE_VERB "${SPROUT_FOLDER_VERB}"
  !insertmacro SPROUT_WRITE_VERB "${SPROUT_BACKGROUND_VERB}"
  ; SHCNE_ASSOCCHANGED: let Explorer pick up the new menu without signing out.
  System::Call 'shell32::SHChangeNotify(i 0x08000000, i 0, p 0, p 0)'
!macroend

!macro NSIS_HOOK_PREUNINSTALL
  ; An update runs the old uninstaller with /UPDATE; keep the menu as the shortcuts are kept.
  ${If} $UpdateMode <> 1
    DeleteRegKey HKCU "${SPROUT_FOLDER_VERB}"
    DeleteRegKey HKCU "${SPROUT_BACKGROUND_VERB}"
    System::Call 'shell32::SHChangeNotify(i 0x08000000, i 0, p 0, p 0)'
  ${EndIf}
!macroend
