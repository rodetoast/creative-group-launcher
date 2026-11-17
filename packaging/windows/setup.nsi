Unicode true
RequestExecutionLevel user
ManifestDPIAware true
!include "MUI2.nsh"
!include "LogicLib.nsh"
!include "FileFunc.nsh"
!include "WinVer.nsh"
!include "x64.nsh"
!include "config.nsh"

Name "${PRODUCT_NAME}"
OutFile "${SETUP_OUTPUT}"
InstallDir "$PROFILE\CGL"
InstallDirRegKey HKCU "${PREF_KEY}" "InstallLocation"
BrandingText "Southpaw Games"
SetCompressor /SOLID lzma
SetCompressorDictSize 32
!define MUI_ICON "${LAUNCHER_ICON}"
!define MUI_UNICON "${LAUNCHER_ICON}"
VIProductVersion "${SETUP_VERSION}"
VIAddVersionKey /LANG=1042 "ProductName" "${PRODUCT_NAME}"
VIAddVersionKey /LANG=1042 "FileDescription" "${PRODUCT_NAME} 설치 프로그램"
VIAddVersionKey /LANG=1042 "FileVersion" "${SETUP_VERSION}"
VIAddVersionKey /LANG=1042 "ProductVersion" "${PRODUCT_VERSION}"
VIAddVersionKey /LANG=1042 "LegalCopyright" "Southpaw Games"

!define MUI_ABORTWARNING
!define MUI_FINISHPAGE_RUN
!define MUI_FINISHPAGE_RUN_FUNCTION StartLauncher
!define MUI_FINISHPAGE_RUN_TEXT "${PRODUCT_NAME} 실행"
!define MUI_FINISHPAGE_TEXT "설치를 완료했습니다.$\r$\n바로가기는 업데이트 후에도 같은 Bootstrap을 사용합니다."
!define MUI_COMPONENTSPAGE_TEXT_TOP "바탕화면 바로가기 생성 여부를 선택해 주세요."
!define MUI_UNCONFIRMPAGE_TEXT_TOP "런처 시작 파일과 바로가기를 제거합니다. 회사 앱, 설정, 작업 파일과 런처 버전 저장소는 보존합니다."
!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_COMPONENTS
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH
!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES
!insertmacro MUI_LANGUAGE "Korean"

Var DataRoot
Var FixedRoot
Var GuardAction
Var GuardLink
Var LockBootstrap
Var LockRunning
Var LockUpdate
Var SetupMutex

!macro GuardFunctions Prefix
Function ${Prefix}RunGuard
  nsExec::ExecToStack '"$PLUGINSDIR\CGLSetupGuard.exe" $GuardAction --root "$INSTDIR" --data "$DataRoot" --link "$GuardLink"'
  Pop $0
  Pop $1
  ${If} $0 != 0
    MessageBox MB_ICONSTOP|MB_OK "$1" /SD IDOK
    SetErrorLevel 1
    Abort
  ${EndIf}
FunctionEnd

Function ${Prefix}CloseLocks
  ${If} $LockBootstrap != ""
    System::Call 'kernel32::CloseHandle(p $LockBootstrap)'
    StrCpy $LockBootstrap ""
  ${EndIf}
  ${If} $LockRunning != ""
    System::Call 'kernel32::CloseHandle(p $LockRunning)'
    StrCpy $LockRunning ""
  ${EndIf}
  ${If} $LockUpdate != ""
    System::Call 'kernel32::CloseHandle(p $LockUpdate)'
    StrCpy $LockUpdate ""
  ${EndIf}
FunctionEnd

Function ${Prefix}AcquireLocks
  CreateDirectory "$INSTDIR\launcher-home\locks"
  System::Call 'kernel32::CreateFileW(w "$INSTDIR\launcher-home\locks\bootstrap.lock", i 0xC0000000, i 7, p 0, i 4, i 0, p 0) p.s'
  Pop $LockBootstrap
  System::Call 'kernel32::LockFile(p $LockBootstrap, i 0, i 0, i 1, i 0) i.r0'
  ${If} $0 == 0
    Goto busy
  ${EndIf}
  System::Call 'kernel32::CreateFileW(w "$INSTDIR\launcher-home\locks\running.lock", i 0xC0000000, i 7, p 0, i 4, i 0, p 0) p.s'
  Pop $LockRunning
  System::Call 'kernel32::LockFile(p $LockRunning, i 0, i 0, i 1, i 0) i.r0'
  ${If} $0 == 0
    Goto busy
  ${EndIf}
  System::Call 'kernel32::CreateFileW(w "$INSTDIR\launcher-home\locks\update.lock", i 0xC0000000, i 7, p 0, i 4, i 0, p 0) p.s'
  Pop $LockUpdate
  System::Call 'kernel32::LockFile(p $LockUpdate, i 0, i 0, i 1, i 0) i.r0'
  ${If} $0 != 0
    Return
  ${EndIf}
busy:
  Call ${Prefix}CloseLocks
  MessageBox MB_ICONSTOP|MB_OK "런처 또는 업데이트 작업이 실행 중입니다. 정상 종료 후 다시 시도해 주세요." /SD IDOK
  SetErrorLevel 1
  Abort
FunctionEnd
!macroend
!insertmacro GuardFunctions ""
!insertmacro GuardFunctions "un."

Function .onInit
  SetShellVarContext current
  SetRegView 64
  ${IfNot} ${RunningX64}
    MessageBox MB_ICONSTOP|MB_OK "Windows 10/11 x64가 필요합니다." /SD IDOK
    Abort
  ${EndIf}
  ${IfNot} ${AtLeastWin10}
    MessageBox MB_ICONSTOP|MB_OK "Windows 10 이상이 필요합니다." /SD IDOK
    Abort
  ${EndIf}
  System::Call 'kernel32::CreateMutexW(p 0, i 0, w "Local\${MUTEX_NAME}") p.r0 ?e'
  Pop $1
  StrCpy $SetupMutex $0
  ${If} $1 == 183
    MessageBox MB_ICONSTOP|MB_OK "같은 설치 프로그램이 이미 실행 중입니다." /SD IDOK
    Abort
  ${EndIf}
  ReadRegStr $FixedRoot HKCU "${PREF_KEY}" "InstallLocation"
  ReadRegStr $DataRoot HKCU "${PREF_KEY}" "DataRoot"
  ${GetParameters} $0
  ${GetOptions} $0 "/DATA=" $1
  ${If} $1 != ""
    ${If} $DataRoot != ""
    ${AndIf} $DataRoot != $1
      MessageBox MB_ICONSTOP|MB_OK "기존 설치의 사용자 데이터 경로를 유지해 주세요." /SD IDOK
      Abort
    ${EndIf}
    StrCpy $DataRoot $1
  ${EndIf}
  ${If} $DataRoot == ""
    StrCpy $DataRoot "$LOCALAPPDATA\SouthpawGames\ToolsLauncher"
  ${EndIf}
  InitPluginsDir
  SetOutPath "$PLUGINSDIR"
  File /oname=CGLSetupGuard.exe "${GUARD_EXE}"
FunctionEnd

Function .onVerifyInstDir
  ${If} $FixedRoot != ""
  ${AndIf} $INSTDIR != $FixedRoot
    SetErrors
  ${EndIf}
FunctionEnd

Section "런처 설치 (필수)" Main
  SectionIn RO
  StrCpy $GuardAction "check-shortcut"
  StrCpy $GuardLink "$SMPROGRAMS\${SHORTCUT_NAME}.lnk"
  Call RunGuard
  SectionGetFlags 1 $0
  IntOp $0 $0 & 1
  ${If} $0 != 0
    StrCpy $GuardLink "$DESKTOP\${SHORTCUT_NAME}.lnk"
    Call RunGuard
  ${EndIf}
  ${If} $FixedRoot != ""
  ${AndIf} $INSTDIR != $FixedRoot
    MessageBox MB_ICONSTOP|MB_OK "재설치에는 기존 설치 위치를 사용해 주세요: $FixedRoot" /SD IDOK
    SetErrorLevel 1
    Abort
  ${EndIf}
  StrCpy $GuardAction "check"
  Call RunGuard
  Call AcquireLocks
  WriteUninstaller "$INSTDIR\Uninstall.exe"
  StrCpy $GuardAction "stamp"
  Call RunGuard
  WriteRegStr HKCU "${PREF_KEY}" "InstallLocation" "$INSTDIR"
  WriteRegStr HKCU "${PREF_KEY}" "DataRoot" "$DataRoot"
  SetOverwrite off
  !include "payload.nsh"
  StrCpy $GuardAction "verify"
  Call RunGuard
  CreateShortCut "$SMPROGRAMS\${SHORTCUT_NAME}.lnk" "$INSTDIR\CGLBootstrap.exe" '--data-dir "$DataRoot"' "$INSTDIR\launcher.ico" 0
  StrCpy $GuardLink "$SMPROGRAMS\${SHORTCUT_NAME}.lnk"
  StrCpy $GuardAction "shortcut"
  Call RunGuard
SectionEnd

Section /o "바탕화면 바로가기 만들기" Desktop
  CreateShortCut "$DESKTOP\${SHORTCUT_NAME}.lnk" "$INSTDIR\CGLBootstrap.exe" '--data-dir "$DataRoot"' "$INSTDIR\launcher.ico" 0
  StrCpy $GuardLink "$DESKTOP\${SHORTCUT_NAME}.lnk"
  StrCpy $GuardAction "shortcut"
  Call RunGuard
SectionEnd

Section "-설치 등록"
  WriteRegStr HKCU "${UNINSTALL_KEY}" "DisplayName" "${PRODUCT_NAME}"
  WriteRegStr HKCU "${UNINSTALL_KEY}" "DisplayVersion" "${PRODUCT_VERSION}"
  WriteRegStr HKCU "${UNINSTALL_KEY}" "SetupVersion" "${SETUP_VERSION}"
  WriteRegStr HKCU "${UNINSTALL_KEY}" "Publisher" "Southpaw Games"
  WriteRegStr HKCU "${UNINSTALL_KEY}" "InstallLocation" "$INSTDIR"
  WriteRegStr HKCU "${UNINSTALL_KEY}" "DisplayIcon" "$INSTDIR\launcher.ico"
  WriteRegStr HKCU "${UNINSTALL_KEY}" "UninstallString" '"$INSTDIR\Uninstall.exe"'
  WriteRegStr HKCU "${UNINSTALL_KEY}" "QuietUninstallString" '"$INSTDIR\Uninstall.exe" /S'
  WriteRegDWORD HKCU "${UNINSTALL_KEY}" "NoModify" 1
  WriteRegDWORD HKCU "${UNINSTALL_KEY}" "NoRepair" 1
  WriteRegDWORD HKCU "${UNINSTALL_KEY}" "SystemComponent" 0
  ${GetSize} "$INSTDIR" "/S=0K" $0 $1 $2
  WriteRegDWORD HKCU "${UNINSTALL_KEY}" "EstimatedSize" $0
SectionEnd

Function StartLauncher
  Exec '"$INSTDIR\CGLBootstrap.exe" --data-dir "$DataRoot"'
FunctionEnd
Function .onInstSuccess
  Call CloseLocks
FunctionEnd
Function .onInstFailed
  Call CloseLocks
FunctionEnd
Function .onGUIEnd
  Call CloseLocks
  System::Call 'kernel32::CloseHandle(p $SetupMutex)'
FunctionEnd

Function un.onInit
  SetShellVarContext current
  SetRegView 64
  ReadRegStr $DataRoot HKCU "${PREF_KEY}" "DataRoot"
  ${If} $DataRoot == ""
    MessageBox MB_ICONSTOP|MB_OK "사용자 데이터 보존 경로를 확인할 수 없습니다." /SD IDOK
    Abort
  ${EndIf}
  InitPluginsDir
  SetOutPath "$PLUGINSDIR"
  File /oname=CGLSetupGuard.exe "${GUARD_EXE}"
FunctionEnd
Function un.onGUIEnd
  Call un.CloseLocks
FunctionEnd

Section "Uninstall"
  StrCpy $GuardAction "uninstall-check"
  Call un.RunGuard
  Call un.AcquireLocks
  StrCpy $GuardAction "remove-shortcut"
  StrCpy $GuardLink "$SMPROGRAMS\${SHORTCUT_NAME}.lnk"
  Call un.RunGuard
  StrCpy $GuardLink "$DESKTOP\${SHORTCUT_NAME}.lnk"
  Call un.RunGuard
  !include "remove-payload.nsh"
  StrCpy $GuardAction "verify-removed"
  Call un.RunGuard
  Delete "$INSTDIR\Uninstall.exe"
  DeleteRegKey HKCU "${UNINSTALL_KEY}"
  Call un.CloseLocks
  DetailPrint "설정, 회사 앱, 작업 파일과 보존된 런처 버전 저장소를 유지했습니다."
SectionEnd
