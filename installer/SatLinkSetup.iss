#ifndef AppVersion
  #define AppVersion "3.0.0"
#endif

#define MyAppName "Sat-Link"
#define MyAppExeName "Sat-Link.exe"
#define MyAppPublisher "Sat-Link Team"

[Setup]
AppId={{A77A7FD8-6C88-4AA3-BB8E-3B52A2A2E7AF}
AppName={#MyAppName}
AppVersion={#AppVersion}
AppVerName={#MyAppName} {#AppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
; Classic wizard flow: Welcome -> License -> Install folder -> Shortcuts -> Ready -> Installing -> Finished
DisableWelcomePage=no
LicenseFile=..\LICENSE
DisableDirPage=no
DisableReadyPage=no
DisableFinishedPage=no
OutputDir=..\release
OutputBaseFilename=SatLink-Setup-{#AppVersion}
SetupIconFile=..\assets\satellite_icon.ico
Compression=lzma
SolidCompression=yes
WizardStyle=modern
UninstallDisplayIcon={app}\{#MyAppExeName}
UninstallDisplayName={#MyAppName}
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
PrivilegesRequired=admin
PrivilegesRequiredOverridesAllowed=dialog

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[Files]
Source: "..\dist\Sat-Link\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs ignoreversion

[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#MyAppName}}"; Flags: nowait postinstall skipifsilent
