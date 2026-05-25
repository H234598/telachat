Unicode true
ManifestDPIAware true

!include "MUI2.nsh"

!ifndef PRODUCT_VERSION
!define PRODUCT_VERSION "dev"
!endif

!ifndef DIST_DIR
!define DIST_DIR "dist"
!endif

Name "Telachat"
OutFile "${DIST_DIR}\TelachatTk-Setup-${PRODUCT_VERSION}.exe"
InstallDir "$LOCALAPPDATA\Telachat"
RequestExecutionLevel user

!define MUI_ABORTWARNING
!define MUI_ICON "${NSISDIR}\Contrib\Graphics\Icons\modern-install.ico"
!define MUI_UNICON "${NSISDIR}\Contrib\Graphics\Icons\modern-uninstall.ico"

!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH

!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES

!insertmacro MUI_LANGUAGE "German"
!insertmacro MUI_LANGUAGE "English"

Section "Telachat" SecMain
    SetOutPath "$INSTDIR"
    File /r "${DIST_DIR}\TelachatTk\*.*"
    CreateDirectory "$SMPROGRAMS\Telachat"
    CreateShortcut "$SMPROGRAMS\Telachat\Telachat.lnk" "$INSTDIR\TelachatTk.exe"
    CreateShortcut "$DESKTOP\Telachat.lnk" "$INSTDIR\TelachatTk.exe"
    WriteUninstaller "$INSTDIR\Uninstall.exe"
SectionEnd

Section "Uninstall"
    Delete "$DESKTOP\Telachat.lnk"
    Delete "$SMPROGRAMS\Telachat\Telachat.lnk"
    RMDir "$SMPROGRAMS\Telachat"
    RMDir /r "$INSTDIR"
SectionEnd
