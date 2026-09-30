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
