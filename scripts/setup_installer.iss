; Inno Setup 6 Script for Steward (Code-Daemon)
#define MyAppName "Steward"
#define MyAppVersion "2.0.0"
#define MyAppPublisher "DeepMind Steward Team"
#define MyAppURL "https://github.com/google/Steward"
#define MyAppExeName "agent_app.exe"
#define MyDaemonExeName "agent_daemon.exe"

[Setup]
AppId={{5A8D2A1C-4B9F-4D2A-9E2B-8C6F1E3D4A5B}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={autopf}\Steward
DisableProgramGroupPage=yes
LicenseFile=..\README.md
OutputDir=..\dist\installer
OutputBaseFilename=Steward2.0_Setup
Compression=lzma
SolidCompression=yes
WizardStyle=modern

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
Name: "envpath"; Description: "Add Steward to System PATH"; GroupDescription: "System Integration"

[Files]
Source: "..\dist\agent_app.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\dist\agent_daemon.exe"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent
