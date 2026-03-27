#ifndef AppVersion
  #define AppVersion "0.0.0-dev"
#endif
#ifndef LauncherSource
  #define LauncherSource "..\..\dist\windows-installer\input\LoRAPilotLauncher.exe"
#endif
#ifndef ManifestUrl
  #define ManifestUrl ""
#endif

#define MyAppName "LoRA Pilot"
#define MyAppPublisher "vavo"
#define MyAppURL "https://github.com/vavo/lora-pilot"

[Setup]
AppId={{3A0C458A-955B-471F-95A1-8C9AF5A9F08B}
AppName={#MyAppName}
AppVersion={#AppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
DefaultDirName={localappdata}\Programs\LoRAPilot
DefaultGroupName={#MyAppName}
OutputBaseFilename=LoRAPilotSetup
OutputDir=..\..\dist\windows-installer
Compression=lzma2
SolidCompression=yes
PrivilegesRequired=admin
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
WizardStyle=modern
DisableProgramGroupPage=yes
ChangesEnvironment=yes
UninstallDisplayIcon={app}\LoRAPilotLauncher.exe

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional shortcuts:"

[Files]
Source: "{#LauncherSource}"; DestDir: "{app}"; DestName: "LoRAPilotLauncher.exe"; Flags: ignoreversion

[Icons]
Name: "{group}\LoRA Pilot"; Filename: "{app}\LoRAPilotLauncher.exe"; Parameters: "start"; WorkingDir: "{app}"
Name: "{group}\Open ControlPilot"; Filename: "{app}\LoRAPilotLauncher.exe"; Parameters: "open"; WorkingDir: "{app}"
Name: "{group}\Stop LoRA Pilot"; Filename: "{app}\LoRAPilotLauncher.exe"; Parameters: "stop"; WorkingDir: "{app}"
Name: "{group}\Uninstall LoRA Pilot"; Filename: "{uninstallexe}"
Name: "{autodesktop}\LoRA Pilot"; Filename: "{app}\LoRAPilotLauncher.exe"; Parameters: "start"; Tasks: desktopicon; WorkingDir: "{app}"

[Run]
Filename: "{app}\LoRAPilotLauncher.exe"; Parameters: "install --manifest-url ""{#ManifestUrl}"""; StatusMsg: "Preparing the managed WSL runtime..."; Flags: waituntilterminated runhidden
Filename: "{app}\LoRAPilotLauncher.exe"; Parameters: "start"; Description: "Launch LoRA Pilot"; Flags: nowait postinstall skipifsilent

[UninstallRun]
Filename: "{app}\LoRAPilotLauncher.exe"; Parameters: "uninstall"; RunOnceId: "LoRAPilotLauncherUninstall"; Flags: runhidden waituntilterminated skipifdoesntexist
