; Instalador do FLUXO360 (Inno Setup 6 - https://jrsoftware.org/isinfo.php)
;
; Como gerar o FLUXO360-Setup.exe (no Windows):
;   1. python instalador\gerar_pacote.py         (monta a pasta dist\FLUXO360)
;   2. Abra este arquivo no Inno Setup e clique em Build > Compile (ou: iscc instalador\FLUXO360.iss)
;   3. O instalador sai em dist\FLUXO360-Setup-<versão>.exe
;
; O Setup copia o programa e depois roda instalar.ps1, que baixa o Python e as bibliotecas
; (precisa de internet). Não pede administrador: instala em %LOCALAPPDATA%\FLUXO360.

#define Versao "1.0.1"

[Setup]
AppId={{02E8D7EE-14AA-435F-A532-F552DF8C7043}
AppName=FLUXO360
AppVersion={#Versao}
AppVerName=FLUXO360 {#Versao}
AppPublisher=Equipe FLUXO360
DefaultDirName={localappdata}\FLUXO360
DefaultGroupName=FLUXO360
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0
OutputDir=..\dist
OutputBaseFilename=FLUXO360-Setup-{#Versao}
SetupIconFile=fluxo360.ico
UninstallDisplayIcon={app}\instalador\fluxo360.ico
UninstallDisplayName=FLUXO360
Compression=lzma2
SolidCompression=yes
WizardStyle=modern

[Languages]
Name: "pt"; MessagesFile: "compiler:Languages\BrazilianPortuguese.isl"

[Types]
Name: "painel"; Description: "Painel (recomendado) - cerca de 500 MB"
Name: "completo"; Description: "Completo: painel + análise de vídeo com YOLO - cerca de 2 GB"

[Components]
Name: "base"; Description: "Painel FLUXO360 e análise de demonstração"; Types: painel completo; Flags: fixed
Name: "analise"; Description: "Análise de vídeo com YOLO (inteligência artificial)"; Types: completo

[Tasks]
Name: "atalho"; Description: "Criar atalho na área de trabalho"; GroupDescription: "Atalhos:"

[Files]
Source: "..\dist\FLUXO360\*"; DestDir: "{app}"; Excludes: "Instalar FLUXO360.bat"; Flags: recursesubdirs createallsubdirs ignoreversion

[Icons]
Name: "{autodesktop}\FLUXO360"; Filename: "{sys}\wscript.exe"; Parameters: """{app}\instalador\iniciar.vbs"""; WorkingDir: "{app}"; IconFilename: "{app}\instalador\fluxo360.ico"; Tasks: atalho
Name: "{group}\FLUXO360"; Filename: "{sys}\wscript.exe"; Parameters: """{app}\instalador\iniciar.vbs"""; WorkingDir: "{app}"; IconFilename: "{app}\instalador\fluxo360.ico"
Name: "{group}\Encerrar FLUXO360"; Filename: "{sys}\WindowsPowerShell\v1.0\powershell.exe"; Parameters: "-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File ""{app}\instalador\encerrar.ps1"""; IconFilename: "{app}\instalador\fluxo360.ico"
Name: "{group}\Reparar FLUXO360"; Filename: "{sys}\WindowsPowerShell\v1.0\powershell.exe"; Parameters: "-NoProfile -ExecutionPolicy Bypass -File ""{app}\instalador\instalar.ps1"" -Destino ""{app}"" -SemCopia -SemAtalhos"; IconFilename: "{app}\instalador\fluxo360.ico"
Name: "{group}\Desinstalar FLUXO360"; Filename: "{uninstallexe}"

[Run]
Filename: "{sys}\wscript.exe"; Parameters: """{app}\instalador\iniciar.vbs"""; Description: "Abrir o FLUXO360 agora"; Flags: postinstall nowait skipifsilent

[UninstallRun]
Filename: "{sys}\WindowsPowerShell\v1.0\powershell.exe"; Parameters: "-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File ""{app}\instalador\encerrar.ps1"" -Silencioso"; Flags: runhidden; RunOnceId: "EncerrarPainel"

[UninstallDelete]
; Criados depois da cópia (Python, bibliotecas, registros). Análises e acompanhamentos do usuário ficam na pasta.
Type: filesandordirs; Name: "{app}\.venv"
Type: filesandordirs; Name: "{app}\ferramentas"
Type: filesandordirs; Name: "{app}\logs"
Type: filesandordirs; Name: "{app}\.streamlit"
Type: filesandordirs; Name: "{app}\data\preferencias"
Type: files; Name: "{app}\instalador\perfil.txt"
Type: files; Name: "{app}\instalador\instalacao_ok.txt"

[Code]
function PerfilEscolhido: String;
begin
  if WizardIsComponentSelected('analise') then
    Result := 'completo'
  else
    Result := 'painel';
end;

procedure CurStepChanged(CurStep: TSetupStep);
var
  ResultCode: Integer;
  Params: String;
begin
  if CurStep = ssPostInstall then
  begin
    WizardForm.StatusLabel.Caption := 'Baixando o Python e as bibliotecas. Pode levar de 5 a 25 minutos...';
    Params := '-NoProfile -ExecutionPolicy Bypass -File "' + ExpandConstant('{app}\instalador\instalar.ps1') +
              '" -Destino "' + ExpandConstant('{app}') + '" -SemCopia -SemAtalhos -Silencioso -Perfil ' + PerfilEscolhido;
    if (not Exec(ExpandConstant('{sys}\WindowsPowerShell\v1.0\powershell.exe'), Params, ExpandConstant('{app}'),
                 SW_SHOW, ewWaitUntilTerminated, ResultCode)) or (ResultCode <> 0) then
      MsgBox('Os arquivos foram copiados, mas o download do Python e das bibliotecas não terminou.' + #13#10 +
             'Confira a internet e use "Reparar FLUXO360" no menu Iniciar.' + #13#10#13#10 +
             'Registro: ' + ExpandConstant('{app}\logs\instalacao.log'), mbError, MB_OK);
  end;
end;
