#define AppName "NewsCollector"
#ifndef AppVersion
#define AppVersion "1.0.0"
#endif
#ifndef SourceDir
#define SourceDir "..\dist\NewsCollector_Portable"
#endif
#ifndef OutputDir
#define OutputDir "..\dist\installer"
#endif

[Setup]
AppId={{B561503D-4855-4C0A-9A3B-53C47D74AB51}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher="NewsCollector Team"
AppPublisherURL="https://example.com"
DefaultDirName={localappdata}\Programs\{#AppName}
DefaultGroupName={#AppName}
DisableProgramGroupPage=no
OutputDir={#OutputDir}
OutputBaseFilename=NewsCollector_Setup
Compression=lzma2
SolidCompression=yes
PrivilegesRequired=lowest
ArchitecturesInstallIn64BitMode=x64
WizardStyle=modern
UninstallDisplayIcon={app}\NewsCollector.exe

[Languages]
Name: "korean"; MessagesFile: "compiler:Languages\\Korean.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Dirs]
Name: "{userappdata}\{#AppName}\data"; Flags: uninsalwaysuninstall
Name: "{userappdata}\{#AppName}\logs"; Flags: uninsalwaysuninstall
Name: "{userappdata}\{#AppName}\results"; Flags: uninsalwaysuninstall

[Files]
Source: "{#SourceDir}\NewsCollector.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#SourceDir}\README.txt"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#SourceDir}\resources\*"; DestDir: "{app}\resources"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "{#SourceDir}\data\*"; DestDir: "{userappdata}\{#AppName}\data"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "{#SourceDir}\logs\*"; DestDir: "{userappdata}\{#AppName}\logs"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "{#SourceDir}\results\*"; DestDir: "{userappdata}\{#AppName}\results"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\{#AppName}"; Filename: "{app}\NewsCollector.exe"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\NewsCollector.exe"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Run]
Filename: "{app}\NewsCollector.exe"; Description: "{#AppName} 실행"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: filesandordirs; Name: "{userappdata}\{#AppName}\data"
Type: filesandordirs; Name: "{userappdata}\{#AppName}\logs"
Type: filesandordirs; Name: "{userappdata}\{#AppName}\results"
