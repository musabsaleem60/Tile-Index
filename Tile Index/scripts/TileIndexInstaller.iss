#define AppName "Tile Index"
#ifndef AppVersion
#define AppVersion "1.0.0"
#endif
#ifndef PackageDir
#define PackageDir "..\dist\TileIndex"
#endif
#ifndef OutputDir
#define OutputDir "..\dist\installer"
#endif
#ifndef CertThumbprint
#define CertThumbprint "5654E094C05235013364F2B2B3ACB04DAB803913"
#endif

[Setup]
AppId={{E8F23DA4-48F3-4E76-9C2A-50E85DB2B41F}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher=Tile Index
DefaultDirName={localappdata}\TileIndex
DefaultGroupName=Tile Index
OutputDir={#OutputDir}
OutputBaseFilename=TileIndexSetup-{#AppVersion}
Compression=lzma2
SolidCompression=yes
PrivilegesRequired=lowest
DisableProgramGroupPage=yes
CloseApplications=yes
RestartApplications=no
SetupLogging=yes
UninstallDisplayIcon={app}\TileIndex.exe

[Files]
Source: "{#PackageDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs; Excludes: "tile_index_config.json"
Source: "{#PackageDir}\tile_index_config.json"; DestDir: "{app}"; Flags: ignoreversion onlyifdoesntexist

[Icons]
Name: "{group}\Tile Index"; Filename: "{app}\TileIndex.exe"
Name: "{autodesktop}\Tile Index"; Filename: "{app}\TileIndex.exe"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Shortcuts:"; Flags: unchecked

[Run]
Filename: "{app}\TileIndex.exe"; Description: "Launch Tile Index"; Flags: nowait postinstall skipifsilent

[Code]
function RunCertUtil(Arguments: String): Boolean;
var
  ResultCode: Integer;
begin
  Result := Exec('certutil.exe', Arguments, '', SW_HIDE, ewWaitUntilTerminated, ResultCode) and (ResultCode = 0);
end;

function TrustStoreContains(StoreName: String): Boolean;
begin
  Result := RunCertUtil('-user -store ' + StoreName + ' {#CertThumbprint}');
end;

procedure CurStepChanged(CurStep: TSetupStep);
var
  CertPath: String;
begin
  if CurStep = ssPostInstall then begin
    CertPath := ExpandConstant('{app}\TileIndex-CodeSigning.cer');
    if not FileExists(CertPath) then begin
      MsgBox('Tile Index was installed, but the update certificate was not found. Updates will not work. Contact your administrator.', mbCriticalError, MB_OK);
      RaiseException('Tile Index update certificate was not found.');
    end;

    if not RunCertUtil('-user -addstore Root "' + CertPath + '"') then begin
      MsgBox('Tile Index could not install the update certificate into Trusted Root. Updates will not work. Contact your administrator.', mbCriticalError, MB_OK);
      RaiseException('Could not install Tile Index update certificate into Trusted Root.');
    end;

    if not RunCertUtil('-user -addstore TrustedPublisher "' + CertPath + '"') then begin
      MsgBox('Tile Index could not install the update certificate into Trusted Publishers. Updates will not work. Contact your administrator.', mbCriticalError, MB_OK);
      RaiseException('Could not install Tile Index update certificate into Trusted Publishers.');
    end;

    if not (TrustStoreContains('Root') and TrustStoreContains('TrustedPublisher')) then begin
      MsgBox('Tile Index installed, but Windows did not verify the update certificate trust. Updates will not work. Contact your administrator.', mbCriticalError, MB_OK);
      RaiseException('Tile Index update certificate trust verification failed.');
    end;
  end;
end;
