;NSIS Modern User Interface
;@env.APPNAME@ Font NSIS Installer script
;Written by Martin Hosken

; This line is included to pull in the MS system.dll plugin rather than the
; stubbed debian one. You should get the MS system.dll and put it in the templates/
; dir or comment out this line if building on windows

; Some useful definitions that may need changing for different font versions
!ifndef VERSION
  !define VERSION @env.VERSION@
!endif

!define FONTNAME "@env.DESC_NAME or env.APPNAME.title()@"
!define SRC_ARCHIVE "ttf-sil-@env.APPNAME@-${VERSION}.zip"
+for f in env.fonts :
!define FONT_@f.id@_FILE "@f.target@"
-
!define INSTALL_SUFFIX "SIL\Fonts\@env.APPNAME.title()@"
!define FONT_DIR "$WINDIR\Fonts"

;-----------------------------
; Macros for Font installation
;-----------------------------
!addplugindir @os.path.join('..', env.basedir, 'nsis')@
!addincludedir @os.path.join('..', env.basedir, 'nsis')@
!include FileFunc.nsh
!include FontRegAdv.nsh
!include FontName.nsh
!include WordFunc.nsh

!insertmacro VersionCompare
!insertmacro GetParent
!insertmacro un.GetFileName

!macro unFontName FONTFILE
  push ${FONTFILE}
  call un.TranslateFontName
  FontName::Name
  call un.CheckFontNameError
!macroend

Function un.TranslateFontName
  !define Index "LINE-${__LINE__}"

  StrCmp $LANGUAGE 1063 0 End-1063 ; Lithuanian (by Vytautas Krivickas)
    Push "Neteisinga rifto versija"
    Push "Planines bylos adreso klaida: %u"
    Push "Planines bylos sukurimo klaida: %u"
    Push "Neteisingas bylos dydis: %u"
    Push "Neteisinga bylos rankena: %u"
    Push "FontName %s ijungiamoji byla i NSIS"
    goto ${Index}
  End-1063:

  StrCmp $LANGUAGE 1031 0 End-1031 ; German (by Jan T. Sott)
    Push "Falsche Fontversion"
    Push "MappedFile Addressfehler: %u"
    Push "MappedFile Fehler: %u"
    Push "Ungültige Dateigrösse: %u"
    Push "Ungültiges Dateihandle %u"
    Push "FontName %s Plugin für NSIS"
    goto ${Index}
  End-1031:

  StrCmp $LANGUAGE 1037 0 End-1037 ; Hebrew (by kichik)
    Push "âøñú ëåôï ùâåéä"
    Push "ùâéàú ëúåáú ÷åáõ îîåôä: %u"
    Push "ùâéàú ÷åáõ îîåôä: %u"
    Push "âåãì ÷åáõ ìà çå÷é: %u"
    Push "éãéú ÷åáõ ìà çå÷éú %u"
    Push "FontName %s plugin for NSIS"
    goto ${Index}
  End-1037:

  StrCmp $LANGUAGE 1046 0 End-1046 ; Portuguese (Brazil) (by deguix)
    Push "Versão de Fonte Errada"
    Push "Erro de Endereço do ArquivoMapeado: %u"
    Push "Erro do ArquivoMapeado: %u"
    Push "Tamanho de arquivo inválido: %u"
    Push "Manuseio de arquivo inválido %u"
    Push "FontName %s plugin para NSIS"
    goto ${Index}
  End-1046:

  StrCmp $LANGUAGE 1025 0 End-1025 ; Arabic (by asdfuae)
    Push "ÅÕÏÇÑ ÇáÎØ ÎÇØÆ"
    Push "ÎØÇÁ ÚäæÇä ÎÑíØÉÇáãáÝ: %u"
    Push "ÎØÇÁ ÎÑíØÉ ÇáãáÝ: %u"
    Push "ÍÌã ÇáãáÝ ÛíÑÕÍíÍ: %u"
    Push "ãÚÇáÌ ÇáãáÝ ÛíÑ ÕÍíÍ %u"
    Push "ãÞÈÓ ÇÓã ÇáÎØ %s áäÓíÓ"
    goto ${Index}
  End-1025:

  StrCmp $LANGUAGE 1028 0 End-1028 ; Chinese (Traditional) by Kii Ali <kiiali@@cpatch.org>
    Push "¿ù»~ªºŠr«¬ª©¥»"
    Push "¹ïÀ³ÀÉ®×Šì§}¿ù»~: %u"
    Push "¹ïÀ³ÀÉ®×¿ù»~: %u"
    Push "µL®ÄªºÀÉ®×€j€p: %u"
    Push "µL®ÄªºÀÉ®×¬`µ{: %u"
    Push "¥Î©ó NSIS ªºŠr«¬ŠWºÙ %s Ž¡¥ó"
    goto ${Index}
  End-1028:

  StrCmp $LANGUAGE 2052 0 End-2052 ; Chinese (Simplified) by Kii Ali <kiiali@@cpatch.org>
    Push "ŽíÎóµÄ×ÖÌå°æ±Ÿ"
    Push "Ó³ÉäÎÄŒþµØÖ·ŽíÎó: %u"
    Push "Ó³ÉäÎÄŒþŽíÎó: %u"
    Push "ÎÞÐ§µÄÎÄŒþŽóÐ¡: %u"
    Push "ÎÞÐ§µÄÎÄŒþ±ú³Ì: %u"
    Push "ÓÃÓÚ NSIS µÄ×ÖÌåÃû³Æ %s ²åŒþ"
    goto ${Index}
  End-2052:

  StrCmp $LANGUAGE 1036 0 End-1036 ; French by evilO/Olive
    Push "Version de police incorrecte"
    Push "Erreur d'adresse du fichier mappé : %u"
    Push "Erreur de fichier mappé : %u"
    Push "Taille de fichier invalide : %u"
    Push "Descripteur de fichier invalide %u"
    Push "FontName %s plugin pour NSIS"
    goto ${Index}
  End-1036:

  StrCmp $LANGUAGE 1034 0 End-1034 ; Spanish (traditional) by Cecilio
    Push "Versión del font incorrecta"
    Push "Error de dirección de archivo mapeado: %u"
    Push "Error de archivo mapeado: %u"
    Push "Tamaño de archivo erroneo: %u"
    Push "Manipulador de archivo erroneo: %u"
    Push "Plugin de NSIS para FontName %s "
    goto ${Index}
  End-1034:

  StrCmp $LANGUAGE 1071 0 End-1071 ; Macedonian by Sasko Zdravkin <wingman2083@@yahoo.com>
    Push "Ïîãðåøíà âåðçèŒà íà Ôîíòîò"
    Push "ÌàïèðàíàòàÄàòîòåêà Ãðåøêà íà àäðåñàòà: %u"
    Push "ÌàïèðàíàòàÄàòîòåêà Ãðåøêà: %u"
    Push "Ïîãðåøíà ãîëåìèíà íà äàòîòåêàòà: %u"
    Push "Ïîãðåøíî ðàêóâàå ñî äàòîòåêàòà: %u"
    Push "FontName %s ïëóãèí çà NSIS"
    goto ${Index}
  End-1071:

; Add your languages here

  ; Default English (1033) by Vytautas Krivickas - MUST REMAIN LAST!
  Push "Wrong Font Version"
  Push "MappedFile Address Error: %u"
  Push "MappedFile Error: %u"
  Push "Invalid file size: %u"
  Push "Invalid file handle %u"
  Push "FontName %s plugin for NSIS"
  goto ${Index}

${Index}:
  !undef Index
FunctionEnd

Function un.CheckFontNameError
  !define Index "LINE-${__LINE__}"

  exch $1
  strcmp $1 "*:*" 0 Index
    pop $1
    exch $1
    SetErrors

Index:
  exch $1
  !undef Index
FunctionEnd
!macro unRemoveTTF FontFile
  Push $0  
  Push $R0
  Push $R1
  Push $R2
  Push $R3
  Push $R4

  !define Index 'Line${__LINE__}'
  
; Get the Font's File name
  ${un.GetFileName} ${FontFile} $0
  !define FontFileName $0

;  DetailPrint "Testing that $FONT_DIR\${FontFileName} exists"
  IfFileExists "$FONT_DIR\${FontFileName}" ${Index} "${Index}-End"

${Index}:
  ClearErrors
  ReadRegStr $R0 HKLM "SOFTWARE\Microsoft\Windows NT\CurrentVersion" "CurrentVersion"
  IfErrors "${Index}-9x" "${Index}-NT"

"${Index}-NT:"
  StrCpy $R1 "Software\Microsoft\Windows NT\CurrentVersion\Fonts"
  goto "${Index}-GO"

"${Index}-9x:"
  StrCpy $R1 "Software\Microsoft\Windows\CurrentVersion\Fonts"
  goto "${Index}-GO"

  !ifdef FontBackup
  "${Index}-GO:"
  ;Implementation of Font Backup Store
    StrCpy $R2 ''
    ReadRegStr $R2 HKLM "${FontBackup}" "${FontFileName}"
    StrCmp $R2 'OK' 0 "${Index}-Skip"

    ClearErrors
    !insertmacro FontName "$FONT_DIR\${FontFileName}"
    pop $R2
    IfErrors 0 "${Index}-Remove"
    MessageBox MB_OK "$R2"
    goto "${Index}-End"    

  "${Index}-Remove:"
    StrCpy $R2 "$R2 (TrueType)"
    System::Call "GDI32::RemoveFontResourceA(t) i ('${FontFileName}') .s"
    DeleteRegValue HKLM "$R1" "$R2"
    DeleteRegValue HKLM "${FontBackup}" "${FontFileName}"
    EnumRegValue $R4 HKLM "${FontBackup}" 0
    IfErrors 0 "${Index}-NoError"
      MessageBox MB_OK "FONT (${FontFileName}) Removal.$\r$\n(Registry Key Error: $R4)$\r$\nRestart computer and try again. If problem persists contact your supplier."
      Abort "EnumRegValue Error: ${FontFileName} triggered error in EnumRegValue for Key $R4."
  "${Index}-NoError:"
    StrCmp $R4 "" 0 "${Index}-NotEmpty"
      DeleteRegKey HKLM "${FontBackup}" ; This will delete the key if there are no more fonts...
  "${Index}-NotEmpty:"
    Delete /REBOOTOK "$FONT_DIR\${FontFileName}"
    goto "${Index}-End"
  "${Index}-Skip:"
    goto "${Index}-End"
  !else
  "${Index}-GO:"
    
    ClearErrors
    !insertmacro unFontName "$FONT_DIR\${FontFileName}"
    pop $R2
;    DetailPrint "Uninstalling font name $R2"
    IfErrors 0 "${Index}-Remove"
    MessageBox MB_OK "$R2"
    goto "${Index}-End"

  "${Index}-Remove:"
    StrCpy $R2 "$R2 (TrueType)"
    System::Call "GDI32::RemoveFontResourceA(t) i ('${FontFileName}') .s"
    DeleteRegValue HKLM "$R1" "$R2"
    delete /REBOOTOK "$FONT_DIR\${FontFileName}"
    goto "${Index}-End"
  !endif

"${Index}-End:"

  !undef Index
  !undef FontFileName

  pop $R4
  pop $R3
  pop $R2
  pop $R1
  Pop $R0  
  Pop $0
!macroend


;--------------------------------
;Include Modern UI

  !include "MUI.nsh"

;--------------------------------
;General

  ;Name and file
  Name "${FONTNAME} Font (${VERSION})"
  Caption "@env.DESC_SHORTER or ""@"

  OutFile "${FONTNAME}-${VERSION}.exe"
  InstallDir $PROGRAMFILES\${INSTALL_SUFFIX}

  ;Get installation folder from registry if available
  InstallDirRegKey HKLM "Software\${INSTALL_SUFFIX}" ""
  
  SetCompressor lzma
;--------------------------------
;Interface Settings

  !define MUI_ABORTWARNING

;--------------------------------
;Pages

  !insertmacro MUI_PAGE_WELCOME
  @'!insertmacro MUI_PAGE_LICENSE "' + os.path.join('..', env.LICENSE) + '"' if env.LICENSE else '"'@
  !insertmacro MUI_PAGE_COMPONENTS
  !insertmacro MUI_PAGE_DIRECTORY
  !insertmacro MUI_PAGE_INSTFILES
  !insertmacro MUI_PAGE_FINISH
  
  !insertmacro MUI_UNPAGE_CONFIRM
  !insertmacro MUI_UNPAGE_INSTFILES
  !define MUI_STARTMENUPAGE
 
  !define MUI_STARTMENUPAGE_REGISTRY_ROOT "HKLM"
  !define MUI_STARTMENUPAGE_REGISTRY_KEY \
    "Software\Microsoft\Windows\CurrentVersion\Uninstall\${FONTNAME}"
  !define MUI_STARTMENUPAGE_REGISTRY_VALUENAME "Start Menu Folder"
  !define MUI_STARTMENUPAGE_FONT_VARIABLE $R9
  !define MUI_STARTMENUPAGE_FONT_DEFAULTFOLDER "SIL\Fonts\@env.APPNAME@"

;--------------------------------
;Languages
 
  !insertmacro MUI_LANGUAGE "English"

  VIAddVersionKey /LANG=${LANG_ENGLISH} "ProductName" "${FONTNAME}"
  VIAddVersionKey /LANG=${LANG_ENGLISH} "ProductVersion" "${VERSION}"
  VIAddVersionKey /LANG=${LANG_ENGLISH} "FileVersion" "${VERSION}"
  VIAddVersionKey /LANG=${LANG_ENGLISH} "CompanyName" "SIL International"
  VIAddVersionKey /LANG=${LANG_ENGLISH} "Comments" "@env.DESC_SHORT or ""@"
  VIAddVersionKey /LANG=${LANG_ENGLISH} "FileDescription" "${FONTNAME} Font installer"
  @'VIAddVersionKey /LANG=${LANG_ENGLISH} "LegalCopyright" "' + env.COPYRIGHT + '"' if env.COPYRIGHT else ""@
  VIProductVersion @env.WINDOWS_VERSION or ".".join((str(env.VERSION).split('.') + ["0", "0", "0", "0"])[0:4])@

;--------------------------------
;Installer Sections

Section "!${FONTNAME} Font" SecFont

  SetOutPath "$WINDIR\Fonts"
  StrCpy $FONT_DIR $FONTS
  
  ReadRegStr $0 HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${FONTNAME}" "Version"
  IfErrors BranchTestRem
  ${VersionCompare} $0 ${VERSION} $R0
  IntCmp $R0 1 BranchQuery BranchQuery BranchUninstall

  BranchQuery:
    MessageBox MB_YESNO|MB_ICONQUESTION "A newer or same version of ${FONTNAME} is already installed. Do you want me to force the installation of this font package?" /SD IDNO IDYES BranchUninstall

  Abort "Installation of ${FONTNAME} aborting"

  BranchUninstall:
    ; execute the uninstaller if it's there else abort
    ReadRegStr $0 HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${FONTNAME}" "UninstallString"
    ${GetParent} "$0" $1
    ExecWait '"$0" /S _?=$1'

  BranchInstall:
    ;ADD YOUR OWN FILES HERE...
    ;File "${FONT_REG_FILE}"  ; done by InstallTTF
    ;File "${FONT_BOLD_FILE}" ; done by InstallTTF

+ for f in env.fonts :
    !insertmacro InstallTTF "@f.target@"
-
    
    SendMessage ${HWND_BROADCAST} ${WM_FONTCHANGE} 0 0 /TIMEOUT=5000
  
    SetOutPath "$INSTDIR"
    ;Default installation folder
  
    ;Store installation folder
    WriteRegStr HKLM "Software\${INSTALL_SUFFIX}" "" $INSTDIR
  
    ;Create uninstaller
    WriteUninstaller "$INSTDIR\Uninstall.exe"

    ; add keys for Add/Remove Programs entry
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${FONTNAME}" \
                 "DisplayName" "${FONTNAME} ${VERSION}"
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${FONTNAME}" \
                 "UninstallString" "$INSTDIR\Uninstall.exe"
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${FONTNAME}" \
                 "Version" "${VERSION}"
    Goto BranchDone

  BranchTestRem:
+for f in env.fonts:
    IfFileExists "$WINDIR/Fonts/@f.target@" 0 BranchNoExist
-
;    IfFileExists "$WINDIR\Fonts\${FONT_REG_FILE}" 0 BranchNoExist
    
    MessageBox MB_YESNO|MB_ICONQUESTION "Would you like to overwrite existing ${FONTNAME} fonts?" /SD IDYES IDYES BranchOverwrite ; skipped if file doesn't exist

    Abort

  BranchOverwrite:
+for f in env.fonts :
    !insertmacro RemoveTTF "@f.target@"
-
      SetOverwrite try
      Goto BranchInstall
  BranchNoExist:
      SetOverwrite ifnewer ; NOT AN INSTRUCTION, NOT COUNTED IN SKIPPINGS
      Goto BranchInstall

  BranchDone:
SectionEnd

Section -StartMenu
  @'File "' + os.path.join('..', env.LICENSE) + '"' if env.LICENSE else ""@
+for dp, dn, fs in os.walk(env.DOCDIR or 'docs') :
+ for fn in fs :
  File "/ONAME=$OUTDIR\@os.path.join(dp, fn).replace('/','\\')@" "@os.path.join(dp, fn)@"
-
-
  !insertmacro MUI_STARTMENU_WRITE_BEGIN "FONT"
  SetShellVarContext all
  CreateDirectory $SMPROGRAMS\${MUI_STARTMENUPAGE_FONT_VARIABLE}
  IfFileExists $SMPROGRAMS\${MUI_STARTMENUPAGE_FONT_VARIABLE} createIcons
    SetShellVarContext current
    CreateDirectory $SMPROGRAMS\${MUI_STARTMENUPAGE_FONT_VARIABLE}
 
  createIcons:
+for dp, dn, fs in os.walk(env.DOCDIR or 'docs') : 
+for fn in fs :
  CreateShortCut $SMPROGRAMS/${MUI_STARTMENUPAGE_FONT_VARIABLE}/@fn@.lnk $OUTDIR/@os.path.join(dp, fn)@
-
-
    CreateShortCut $SMPROGRAMS\${MUI_STARTMENUPAGE_FONT_VARIABLE}\Uninstall.lnk $INSTDIR\Uninstall.exe
    WriteRegStr ${MUI_STARTMENUPAGE_REGISTRY_ROOT} "${MUI_STARTMENUPAGE_REGISTRY_KEY}" "Menus" "$SMPROGRAMS\${MUI_STARTMENUPAGE_FONT_VARIABLE}"
  !insertmacro MUI_STARTMENU_WRITE_END
SectionEnd

;Optional source font - as a compressed archive
Section "Documentation" SecSrc

  SetOutPath "$INSTDIR"
  SetOverwrite ifnewer
  ;ADD YOUR OWN FILES HERE...
+d = {}; 
+ for f in (env.EXTRA_DIST or '').split(' ') :
+  if f and not os.path.dirname(f) in d :
  CreateDirectory @os.path.dirname(f).replace('/','\\')@
-d[f] = 1
-
-
+for f in (env.EXTRA_DIST or '').split(' ') :
  @'File "/ONAME=$OUTDIR\\' + f.replace('/','\\') + '" "' + f.replace('/', '\\') + '"' if f else ""@
-
  
SectionEnd


;--------------------------------
;Descriptions

  ;Language strings
  LangString DESC_SecFont ${LANG_ENGLISH} "Install the ${FONTNAME} font (version ${VERSION}). @env.DESC_SHORT or ""@"
;  LangString DESC_SecSrc ${LANG_ENGLISH} "Install the source font and Graphite code for ${FONTNAME} (version ${VERSION}). You only need this if you are a font developer."


  ;Assign language strings to sections
  !insertmacro MUI_FUNCTION_DESCRIPTION_BEGIN
    !insertmacro MUI_DESCRIPTION_TEXT ${SecFont} $(DESC_SecFont)
;    !insertmacro MUI_DESCRIPTION_TEXT ${SecSrc} $(DESC_SecSrc)
  !insertmacro MUI_FUNCTION_DESCRIPTION_END

;--------------------------------
;Uninstaller Section

Section "Uninstall"

  ;ADD YOUR OWN FILES HERE...

; uninstaller can only call unFunctions!!
;    !insertMacro RemoveFON "${FONT_REG_FILE}" "${FONTNAME} (TrueType)"
;    !insertMacro RemoveFON "${FONT_BOLD_FILE}" "${FONTNAME} Bold (TrueType)"
;    SendMessage ${HWND_BROADCAST} ${WM_FONTCHANGE} 0 0 /TIMEOUT=5000

    StrCpy $FONT_DIR $FONTS
;    DetailPrint "unRemoveTTF ${FONT_REG_FILE}"
+for f in env.fonts :
    !insertmacro unRemoveTTF "@f.target@"
-
;  Delete  /REBOOTOK "$WINDIR\Fonts\${FONT_REG_FILE}"
;  Delete  /REBOOTOK "$WINDIR\Fonts\${FONT_BOLD_FILE}"
  SendMessage ${HWND_BROADCAST} ${WM_FONTCHANGE} 0 0 /TIMEOUT=5000
  
;  !insertmacro MUI_STARTMENU_GETFOLDER FONT ${MUI_STARTMENU_FONT_VARIABLE}
  ReadRegStr $0 HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${FONTNAME}" "Menus"
+for f in (env.EXTRA_DIST or '').split(' ') :
  Delete "$INSTDIR\\@f.replace('/','\\')@"
-
+for dp, dn, fs in os.walk(env.DOCDIR or 'docs') :
+ for fn in fs :
  Delete "$INSTDIR\@os.path.join(dp, fn).replace('/','\\')@"
-
-
  Delete "$INSTDIR\Uninstall.exe"
+d = {}; 
+for f in (env.EXTRA_DIST or '').split(' ') :
+ if not os.path.dirname(f) in d :
  RmDir "$INSTDIR\@os.path.dirname(f).replace('/','\\')@"
-d[f] = 1
-
-
  RMDir "$INSTDIR"
+for dp, dn, fs in os.walk(env.DOCTDIR or 'docs') :
+ for fn in fs :
  Delete "$0\@fn@.lnk"
-
-
  Delete "$0\Uninstall.lnk"
  RMDir "$0"


;  ReadRegStr $0 "${MUI_STARTMENUPAGE_REGISTRY_ROOT}" \
;    "${MUI_STARTMENUPAGE_REGISTRY_KEY}" "${MUI_STARTMENUPAGE_REGISTRY_VALUENAME}"
 
;  StrCmp $0 "" noshortcuts
;    foreach f,$(DOCS),$(sub /,\,Delete $0/$(f))
;    Delete $0\Uninstall.lnk
;    Delete $0\License.lnk
;    RMDir $0
 
  noshortcuts:

;  DeleteRegKey /ifempty HKLM "Software\${INSTALL_SUFFIX}"
  DeleteRegKey HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${FONTNAME}"

SectionEnd

