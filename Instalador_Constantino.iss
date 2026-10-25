#define AppName "Constantino Software - Organizador Inteligente"
#define AppVersion "0.10.0-beta"
#define AppExe "ConstantinoOrganizador.exe"
[Setup]
AppId={{A2A8EB62-3E0D-42B4-BFB0-A83E5F2218A7}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher=Constantino Software
DefaultDirName={localappdata}\Programs\Constantino Software
DefaultGroupName=Constantino Software
OutputDir=INSTALADOR_PRONTO
OutputBaseFilename=Instalar_Constantino_Software_0_10_0_beta
Compression=lzma
SolidCompression=yes
PrivilegesRequired=lowest
WizardStyle=modern
UninstallDisplayIcon={app}\{#AppExe}
[Files]
Source: "dist\ConstantinoOrganizador\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
[Icons]
Name: "{autoprograms}\Constantino Software"; Filename: "{app}\{#AppExe}"
Name: "{autodesktop}\Constantino Software"; Filename: "{app}\{#AppExe}"; Tasks: desktopicon
[Tasks]
Name: desktopicon; Description: "Criar atalho na area de trabalho"; GroupDescription: "Atalhos:"; Flags: checkedonce
[Run]
Filename: "{app}\{#AppExe}"; Description: "Abrir Constantino Software"; Flags: nowait postinstall skipifsilent
