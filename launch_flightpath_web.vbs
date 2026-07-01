Set shell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
base = fso.GetParentFolderName(WScript.ScriptFullName)
cmd = "cmd /c cd /d """ & base & """ && run_web_app.bat"
shell.Run cmd, 0, False
