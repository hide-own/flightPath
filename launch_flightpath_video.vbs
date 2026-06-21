Set shell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
root = fso.GetParentFolderName(WScript.ScriptFullName)
pythonw = root & "\.venv\Scripts\pythonw.exe"
launcher = root & "\flightpath_video_launcher.pyw"

If Not fso.FileExists(pythonw) Then
    MsgBox "Cannot start: .venv\Scripts\pythonw.exe was not found. Please create the virtual environment and install dependencies first.", vbCritical, "FlightPath Video"
    WScript.Quit 1
End If

If Not fso.FileExists(launcher) Then
    MsgBox "Cannot start: launcher file was not found.", vbCritical, "FlightPath Video"
    WScript.Quit 1
End If

shell.CurrentDirectory = root
shell.Run """" & pythonw & """ """ & launcher & """", 0, False
