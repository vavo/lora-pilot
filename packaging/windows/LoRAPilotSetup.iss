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
#define MyAppURL "https://lorapilot.com"

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
WizardImageFile=assets\lorapilot-wizard-image.png
WizardSmallImageFile=assets\lorapilot-wizard-small.png
DisableProgramGroupPage=yes
ChangesEnvironment=yes
UninstallDisplayIcon={app}\LoRAPilotLauncher.exe

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional shortcuts:"

[Files]
Source: "{#LauncherSource}"; DestDir: "{app}"; DestName: "LoRAPilotLauncher.exe"; Flags: ignoreversion
Source: "Run-LoRAPilotManagedSetup.ps1"; DestDir: "{app}"; Flags: ignoreversion

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
  WebsiteLink: TNewStaticText;

function NeedRestart(): Boolean;
begin
  Result := ManagedInstallNeedsRestart;
end;

procedure OpenWebsite(Sender: TObject);
var
  ResultCode: Integer;
begin
  ShellExec('open', '{#MyAppURL}', '', '', SW_SHOWNORMAL, ewNoWait, ResultCode);
end;

procedure CreateWebsiteLink();
begin
  WebsiteLink := TNewStaticText.Create(WizardForm);
  WebsiteLink.Parent := WizardForm;
  WebsiteLink.Caption := 'Visit lorapilot.com';
  WebsiteLink.Cursor := crHand;
  WebsiteLink.Font.Color := clBlue;
  WebsiteLink.Font.Style := [fsUnderline];
  WebsiteLink.AutoSize := True;
  WebsiteLink.Left := WizardForm.CancelButton.Left - WebsiteLink.Width - ScaleX(18);
  WebsiteLink.Top := WizardForm.CancelButton.Top + ScaleY(6);
  WebsiteLink.OnClick := @OpenWebsite;
end;

procedure InitializeWizard();
begin
  CreateWebsiteLink();
end;

procedure RunManagedInstall();
var
  ResultCode: Integer;
  ExecOk: Boolean;
  LauncherPath: string;
  ProgressScriptPath: string;
  PowerShellPath: string;
  Parameters: string;
begin
  LauncherPath := ExpandConstant('{app}\LoRAPilotLauncher.exe');
  ProgressScriptPath := ExpandConstant('{app}\Run-LoRAPilotManagedSetup.ps1');
  PowerShellPath := ExpandConstant('{sys}\WindowsPowerShell\v1.0\powershell.exe');
  Parameters := '-NoLogo -NoProfile -NonInteractive -ExecutionPolicy Bypass -STA ' +
    '-WindowStyle Hidden ' +
    '-File "' + ProgressScriptPath + '" ' +
    '-LauncherPath "' + LauncherPath + '" ' +
    '-ManifestUrl "{#ManifestUrl}" ' +
    '-Launch';
  WizardForm.StatusLabel.Caption := 'Preparing the LoRA Pilot runtime...';

  WizardForm.Hide;
  try
    ExecOk := Exec(PowerShellPath, Parameters, ExpandConstant('{app}'), SW_HIDE, ewWaitUntilTerminated, ResultCode);
  finally
    WizardForm.Show;
  end;
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
