; Build with Inno Setup 6 after PyInstaller, from the repository root.
#define AppName "Registro Docente"
#define AppVersion "1.8.1"
[Setup]
AppId={{B248D8D2-1C74-4E8B-A107-43F49F9CC8B2}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher=Leonardo Roque
AppCopyright=Leonardo Roque
VersionInfoCompany=Leonardo Roque
VersionInfoCopyright=Leonardo Roque
DisableWelcomePage=no
DefaultDirName={localappdata}\Programs\RegistroDocente
DefaultGroupName={#AppName}
PrivilegesRequired=lowest
OutputDir=..\dist\installer
OutputBaseFilename=RegistroDocente-Setup
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
ChangesAssociations=yes
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
UninstallDisplayIcon={app}\RegistroDocente.exe
[Languages]
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"
[Messages]
spanish.WelcomeLabel2=Este programa pertenece a Leonardo Roque.%n%nEl asistente instalará [name/ver] en su computadora. Sus registros y respaldos se conservan al actualizar.
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

[Registry]
Root: HKCU; Subkey: "Software\Classes\.registro"; ValueType: string; ValueName: ""; ValueData: "RegistroDocente.Documento"; Flags: uninsdeletevalue
Root: HKCU; Subkey: "Software\Classes\RegistroDocente.Documento"; ValueType: string; ValueName: ""; ValueData: "Documento de Registro Docente"; Flags: uninsdeletekey
Root: HKCU; Subkey: "Software\Classes\RegistroDocente.Documento\DefaultIcon"; ValueType: string; ValueName: ""; ValueData: "{app}\RegistroDocente.exe,0"
Root: HKCU; Subkey: "Software\Classes\RegistroDocente.Documento\shell\open\command"; ValueType: string; ValueName: ""; ValueData: """{app}\RegistroDocente.exe"" ""%1"""
