#ifndef AppVersion
  #define AppVersion "0.0.0-dev"
#endif
#ifndef LauncherSource
  #define LauncherSource "..\..\dist\windows-installer\input\LoRAPilotLauncher.exe"
#endif
#ifndef ManifestUrl
  #define ManifestUrl ""
#endif
#ifndef AutoInstall
  #define AutoInstall 0
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

[UninstallRun]
Filename: "{app}\LoRAPilotLauncher.exe"; Parameters: "uninstall"; RunOnceId: "LoRAPilotLauncherUninstall"; Flags: runhidden waituntilterminated skipifdoesntexist

[Code]
const
  SetupResumeScheduledExitCode = 42;

var
  ManagedInstallNeedsRestart: Boolean;

function NeedRestart(): Boolean;
begin
  Result := ManagedInstallNeedsRestart;
end;

procedure RunManagedInstall();
var
  ResultCode: Integer;
  ExecOk: Boolean;
  LauncherPath: string;
  Parameters: string;
begin
  LauncherPath := ExpandConstant('{app}\LoRAPilotLauncher.exe');
  Parameters := 'setup --launch --manifest-url "{#ManifestUrl}"';
  WizardForm.StatusLabel.Caption := 'Downloading and preparing the LoRA Pilot runtime...';

  ExecOk := Exec(LauncherPath, Parameters, ExpandConstant('{app}'), SW_HIDE, ewWaitUntilTerminated, ResultCode);
  if not ExecOk then begin
    SuppressibleMsgBox(
      'LoRA Pilot could not start its managed runtime setup.' + #13#10 + #13#10 +
      'Check the launcher log at:' + #13#10 +
      ExpandConstant('{localappdata}\LoRAPilot\logs\launcher.log'),
      mbCriticalError,
      MB_OK,
      IDOK
    );
    Abort;
  end;

  if ResultCode = 0 then
    Exit;

  if ResultCode = SetupResumeScheduledExitCode then begin
    ManagedInstallNeedsRestart := True;
    SuppressibleMsgBox(
      'Windows finished installing WSL components and must restart to finish LoRA Pilot setup.' + #13#10 + #13#10 +
      'LoRA Pilot will resume setup automatically after the next sign-in.',
      mbInformation,
      MB_OK,
      IDOK
    );
    Exit;
  end;

  SuppressibleMsgBox(
    'LoRA Pilot setup could not finish.' + #13#10 + #13#10 +
    'See the launcher log for details:' + #13#10 +
    ExpandConstant('{localappdata}\LoRAPilot\logs\launcher.log'),
    mbCriticalError,
    MB_OK,
    IDOK
  );
  Abort;
end;

procedure CurStepChanged(CurStep: TSetupStep);
begin
  if (CurStep = ssPostInstall) and ('{#AutoInstall}' = '1') then
    RunManagedInstall();
end;
