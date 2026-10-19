; Inno Setup script for ChitSetup.exe. Build with packaging\build.ps1, which passes
; /DAppVersion=<version from src\chit\__init__.py>.
#define AppName "Chit"
#ifndef AppVersion
  #define AppVersion "0.0.0"
#endif
#define AppExe "Chit.exe"

[Setup]
AppId={{6D2B7C1E-3F4A-4E8B-9C5D-2A7E1B9F4C30}
AppName={#AppName}
AppVersion={#AppVersion}
AppVerName={#AppName} {#AppVersion}
AppPublisher=ReportedGuy
AppPublisherURL=https://github.com/reportedguy/chit
AppSupportURL=https://github.com/reportedguy/chit/issues
VersionInfoVersion={#AppVersion}
VersionInfoDescription=Chit voice dictation setup
DefaultDirName={localappdata}\Programs\{#AppName}
DisableProgramGroupPage=yes
DisableDirPage=yes
PrivilegesRequired=lowest
OutputDir=..\build
OutputBaseFilename=ChitSetup
SetupIconFile=chit.ico
WizardSmallImageFile=wizard_small.bmp
UninstallDisplayIcon={app}\{#AppExe}
UninstallDisplayName={#AppName}
Compression=lzma2/ultra64
SolidCompression=yes
; The compiler is 32-bit; compress in a separate 64-bit process so large bundles fit in memory.
LZMAUseSeparateProcess=yes
LZMANumBlockThreads=2
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
CloseApplications=force
MinVersion=10.0.17763

[Tasks]
Name: "startup"; Description: "Start Chit when I sign in to Windows"
Name: "desktopicon"; Description: "Create a desktop shortcut"; Flags: unchecked

[Files]
Source: "..\build\dist\Chit\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\{#AppName}"; Filename: "{app}\{#AppExe}"; Comment: "Hold Caps Lock to dictate"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExe}"; Tasks: desktopicon

[Registry]
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: string; ValueName: "{#AppName}"; \
  ValueData: """{app}\{#AppExe}"" --background"; Flags: uninsdeletevalue; Tasks: startup

[Run]
Filename: "{app}\{#AppExe}"; Description: "Start Chit now"; Flags: nowait postinstall skipifsilent

[UninstallRun]
Filename: "{sys}\taskkill.exe"; Parameters: "/F /T /IM {#AppExe}"; Flags: runhidden; RunOnceId: "StopChit"

[Code]
procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
begin
  if CurUninstallStep = usUninstall then
    { The tray menu's "Start at login" writes this too, even if the install task was off. }
    RegDeleteValue(HKCU, 'Software\Microsoft\Windows\CurrentVersion\Run', '{#AppName}');
  if CurUninstallStep = usPostUninstall then
    if UninstallSilent or
       (MsgBox('Also delete Chit''s downloaded models and settings (about 1.4 GB)?',
               mbConfirmation, MB_YESNO) = IDYES) then
      DelTree(ExpandConstant('{localappdata}\{#AppName}'), True, True, True);
end;
