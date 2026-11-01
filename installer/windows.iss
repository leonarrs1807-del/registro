; Build with Inno Setup 6 after PyInstaller, from the repository root.
#define AppName "Registro Docente"
#define AppVersion "1.1.0"
[Setup]
AppId={{B248D8D2-1C74-4E8B-A107-43F49F9CC8B2}
AppName={#AppName}
AppVersion={#AppVersion}
DefaultDirName={localappdata}\Programs\RegistroDocente
DefaultGroupName={#AppName}
PrivilegesRequired=lowest
OutputDir=..\dist\installer
OutputBaseFilename=RegistroDocente-Setup
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
UninstallDisplayIcon={app}\RegistroDocente.exe
[Languages]
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"
[Tasks]
Name: "desktopicon"; Description: "Crear acceso directo en el escritorio"; Flags: unchecked
[Files]
Source: "..\dist\RegistroDocente\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\RegistroDocente.exe"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\RegistroDocente.exe"; Tasks: desktopicon
[Run]
Filename: "{app}\RegistroDocente.exe"; Description: "Abrir Registro Docente"; Flags: nowait postinstall skipifsilent
; User data in LOCALAPPDATA\RegistroDocente is deliberately retained on uninstall.
